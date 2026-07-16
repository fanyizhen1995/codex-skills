---
source_id: sglang-github-closed-issues-prs
title: '[Bug][Perf] Unnecessary sync in flashinfer attn backend for Qwen3.5-397B-A17B-FP8
  model'
canonical_url: https://github.com/sgl-project/sglang/issues/23500
captured_at: '2026-07-13T23:40:05.154373+00:00'
content_hash: f5a920378922eca23199c59d2ece266d72202bfd356dbacd7d5161eb1528b7f5
---
# [Bug][Perf] Unnecessary sync in flashinfer attn backend for Qwen3.5-397B-A17B-FP8 model

URL: https://github.com/sgl-project/sglang/issues/23500
State: closed
Labels: inactive
Closed at: 2026-07-13T00:36:24Z
Merged at: 

## Summary

While profiling Qwen3.5-397B-A17B-FP8 with EAGLE speculative decoding, the scheduler's event loop shows a long `cudaMemcpyAsync` on the CPU critical path **every decode iteration**, inside FlashInfer's prefill `plan()`. It is reached from the EAGLE v2 **draft-extend** path (`ForwardMode.DRAFT_EXTEND_V2`) and the analogous **verify** path. Because `event_loop_overlap` serializes on it, the sync directly stretches per-step latency at steady state.

The decode side of FlashInfer already has a CPU-indptr override (`fast_decode_plan` / `global_override_indptr_cpu`), which is why normal decode is fine. **No equivalent exists for the prefill wrapper**, so EAGLE draft-extend + verify pay this sync on every iteration.

<img width="925" height="448" alt="Image" src="https://github.com/user-attachments/assets/5fbc5294-e1cb-46bf-970f-fbed0d99adc3" />

## Environment

- Commit: `917d2aa1dc2ada0db9c5e2c3d9e10d531849a0bb` (main)
- Model: `Qwen/Qwen3.5-397B-A17B-FP8`
- Topology: TP=8
- Backend: FlashInfer (via `hybrid_linear_attn_backend` — Qwen3.5 mixes full-attn + linear-attn layers)
- Features enabled: `SGLANG_ENABLE_SPEC_V2=1`, `--enable-flashinfer-allreduce-fusion`, `--mamba-scheduler-strategy extra_buffer`, `--page-size 64`
- Env: torch 2.9.1+cu128, CUDA 12.8 (nvcc 12.8.93), cuDNN 9.10.2, flashinfer 0.6.7.post3, sgl_kernel 0.4.1, driver 580.126.09, 8× H100 80GB HBM3 

## Reproduction

```bash
SGLANG_ENABLE_SPEC_V2=1 python -m sglang.launch_server \
  --model-path Qwen/Qwen3.5-397B-A17B-FP8 --tp 8 \
  --reasoning-parser qwen3 --tool-call-parser qwen3_coder \
  --speculative-algorithm EAGLE --speculative-num-steps 3 \
  --speculative-eagle-topk 1 --speculative-num-draft-tokens 4 \
  --mamba-scheduler-strategy extra_buffer --page-size 64 \
  --enable-flashinfer-allreduce-fusion --mem-fraction-static 0.8 \
  --skip-server-warmup --host 0.0.0.0 --port 30088
```

Drive traffic with any generation benchmark, then capture a torch profiler trace around `event_loop_overlap`, and view in Perfetto.

### Observed call stack (from Perfetto)

```
python/sglang/srt/managers/scheduler.py:3659  dispatch_event_loop
python/sglang/srt/managers/scheduler.py:1426  event_loop_overlap
python/sglang/srt/managers/scheduler.py:2751  run_batch
python/sglang/srt/speculative/eagle_worker_v2.py     forward_batch_generation
python/sglang/srt/speculative/eagle_worker_v2.py     _draft_extend_for_decode
python/sglang/srt/speculative/eagle_info_v2.py:207   prepare_for_extend_to_fill_draft_kvcache
python/sglang/srt/layers/attention/hybrid_linear_attn_backend.py:739  init_forward_metadata
python/sglang/srt/layers/attention/flashinfer_backend.py:425          init_forward_metadata
python/sglang/srt/layers/attention/flashinfer_backend.py:1241         update_single_wrapper
python/sglang/srt/layers/attention/flashinfer_backend.py:1372         call_begin_forward
flashinfer/prefill.py:1657                                            plan
  → <Tensor>.to("cpu")  → aten::to → aten::_to_copy → aten::copy_ → cudaMemcpyAsync
```

(Screenshot: will attach below — CPU timeline showing the `cudaMemcpyAsync` slice under `flashinfer/prefill.py:1657 plan`.)

## Root cause

`BatchPrefillWithPagedKVCacheWrapper.plan()` in FlashInfer needs CPU-side `qo_indptr` / `kv_indptr` for its scheduling logic (split-KV, per-request work distribution). When SGLang hands it GPU tensors, `plan()` does an internal `.to("cpu")`. That single copy:

1. is itself a D→H `cudaMemcpyAsync`, and
2. forces the host to wait on the just-produced GPU `cumsum` that computed the indptr — serializing the CPU event loop against prior GPU work.

The indptr values are **trivially computable on CPU** (batch size, `draft_token_num`, `seq_lens_cpu` are all already on host), but current code produces them on GPU and lets FlashInfer round-trip them back.

### Where the GPU indptr are built

**Draft-extend** — `python/sglang/srt/speculative/eagle_info.py` `EagleDraftInput.generate_attn_arg_prefill` (lines 165-221):

```python
device = req_pool_indices.device  # CUDA
qo_indptr = torch.arange(0, (1 + batch_size) * self.draft_token_num,
                         step=self.draft_token_num, ..., device=device)   # L174 — GPU arange
cum_kv_seq_len = torch.zeros((batch_size + 1,), ..., device=device)       # L181
paged_kernel_lens = paged_kernel_lens + self.draft_token_num              # L185
cum_kv_seq_len[1:] = torch.cumsum(paged_kernel_lens, dim=0)               # L186 — GPU cumsum
kv_indices = torch.empty(..., device=device)                              # L188 — must be GPU
```

**Verify** — `python/sglang/srt/speculative/eagle_info.py` `EagleVerifyInput.generate_attn_arg_prefill` (lines 749-779):

```python
qo_indptr = torch.zeros((bs + 1,), ..., device=device)                    # L758
qo_indptr[1:] = torch.cumsum(self.accept_length, dim=0)                   # L759 — GPU cumsum
cum_kv_seq_len = torch.zeros((bs + 1,), ..., device=device)               # L760
cum_kv_seq_len[1:] = torch.cumsum(paged_kernel_lens, dim=0)               # L761 — GPU cumsum
```

Only `kv_indices` genuinely needs the GPU (filled by `create_flashinfer_kv_indices_triton`). The two indptr tensors are the ones FlashInfer ends up `.to("cpu")`'ing.

### Where the sync lands

`python/sglang/srt/layers/attention/flashinfer_backend.py` `FlashInferIndicesUpdaterPrefill.call_begin_forward` (lines 1380-1487), specifically the `spec_info is not None` branch at L1422-1431 followed by:

```python
wrapper_paged.begin_forward(                         # L1469
    qo_indptr,                                       # GPU
    kv_indptr,                                       # GPU
    kv_indices,                                      # GPU
    self.kv_last_page_len[:bs],
    ...
    non_blocking=True,                               # ineffective — plan() syncs internally
    ...
)
```

`wrapper_paged.begin_forward` is FlashInfer's stock prefill `plan()` — no CPU-override kwarg — so it does `.to("cpu")` on the two indptr tensors, which becomes the observed `cudaMemcpyAsync`.

### Dispatch path from the attention backend

`flashinfer_backend.py:425` `init_forward_metadata` → `is_draft_extend()` dispatch at L447 → `indices_updater_prefill.update_single_wrapper` (L1249) → `call_begin_forward` (L1380).

## Why decode isn't affected (existing precedent)

FlashInfer exposes `fast_decode_plan` which accepts `global_override_indptr_cpu`. SGLang already uses it for the decode path:

- Import at `python/sglang/srt/layers/attention/flashinfer_backend.py:53`:
  ```python
  from flashinfer import (..., fast_decode_plan, ...)
  ```
- Installation at L599:
  ```python
  decode_wrappers[i].begin_forward = functools.partial(fast_decode_plan, decode_wrappers[i])
  ```
- Build + pass-through at L1145-1178:
  ```python
  global global_override_indptr_cpu
  if seq_lens_cpu is not None and global_override_indptr_cpu is None:
      global_override_indptr_cpu = torch.empty_like(kv_indptr, device="cpu")
      global_override_indptr_cpu[0] = 0
      global_override_indptr_cpu[1 : bs + 1] = torch.cumsum(seq_lens_cpu, dim=0)  # CPU cumsum
  ...
  wrapper.begin_forward(..., global_override_indptr_cpu=global_override_indptr_cpu)  # L1177
  ```

Even multi-step draft-**decode** caches one `.cpu()` per batch — `FlashInferMultiStepDraftBackend.common_template` at L1568-1580:

```python
# Copy the kv_indptr once to avoid multiple device-to-host copies in flashinfer's plan.
indptr_cpu_whole = self.kv_indptr[:, : bs + 1].cpu()
for i in range(self.speculative_num_steps - 1):
    global_override_indptr_cpu = indptr_cpu_whole[i]
    call_fn(i, forward_batch)
```

None of this applies to the prefill wrapper.

## Impact

- Fires on **every decode iteration** when EAGLE v2 is active (steady-state generation, not just warmup).
- With `--speculative-num-steps 3 --speculative-num-draft-tokens 4`, both **draft-extend** and **verify** hit the same prefill `plan()` each step.
- On TP=8 Qwen3.5 with hybrid linear attention, the sync is clearly visible on the scheduler's CPU timeline and is not overlappable with compute — `event_loop_overlap` waits on it.
- Any EAGLE v2 deployment using the FlashInfer attention backend is affected; Qwen3.5 is how this reproduces cleanly.
