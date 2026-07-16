---
source_id: sglang-github-closed-issues-prs
title: '[Bug] MiMo-V2.5 multi-layer EAGLE × triton attention: draft extend step≥1
  fails with kv_indices=None triton CompilationError'
canonical_url: https://github.com/sgl-project/sglang/issues/24481
captured_at: '2026-07-12T23:38:53.048573+00:00'
content_hash: 8ae119b32d2ccaf5de5593335da04e3404acc05fc873c3771cd61afc3622d62d
---
# [Bug] MiMo-V2.5 multi-layer EAGLE × triton attention: draft extend step≥1 fails with kv_indices=None triton CompilationError

URL: https://github.com/sgl-project/sglang/issues/24481
State: closed
Labels: inactive
Closed at: 2026-07-12T00:35:44Z
Merged at: 

### Summary

`XiaomiMiMo/MiMo-V2.5` with `--speculative-algorithm EAGLE --attention-backend triton` crashes during `MultiLayerEagleMultiStepDraftExtendCudaGraphRunner` capture at step≥1. The triton `extend_attention._fwd_kernel` receives `kv_indices=None` while `SLIDING_WINDOW_SIZE>0` (MiMo MTP draft layers reuse the target's SWA attention), and the kernel unconditionally does `tl.load(kv_indices + ...)` in the SWA branch.

This blocks MTP on any hardware where `triton` is the only viable attention backend (e.g. SM120 / RTX PRO 6000 Blackwell, where fa3 is excluded by `vision.py:963` / flash-attn #1853, and fa4 paged-KV asserts `"Paged KV not supported on SM 12.0"`).

The same model+EAGLE config works on H200 with `--attention-backend fa3` (#23811 CI, GSM8K=0.925, accept=3.36) because FA kernels use `page_table` instead of `kv_indices`.

### Environment

- Hardware: GCP `g4-standard-384`, 4× NVIDIA RTX PRO 6000 Blackwell Server Edition (SM 12.0), driver 580.126.20
- Image: `lmsysorg/sglang:dev-cu13-mimo-v2.5` (sha `983cd01`, day-0 PR #23811)
- Model: `XiaomiMiMo/MiMo-V2.5` (310.7B, FP8 e4m3 block-scale [128,128], 3× MTP modules with SWA attention)

### Repro

```bash
docker run --rm --runtime=nvidia --ipc=host --shm-size=250g --network=host \
  -e CUDA_VISIBLE_DEVICES=0,1,2,3 \
  -e SGLANG_DISABLE_DEEP_GEMM=1 \
  -v /weights/MiMo-V2.5:/weights:ro \
  lmsysorg/sglang:dev-cu13-mimo-v2.5 \
  python3 -m sglang.launch_server \
    --model-path /weights --trust-remote-code --tp 4 \
    --attention-backend triton \
    --mm-attention-backend triton_attn \
    --fp8-gemm-backend triton --ep-size 4 \
    --mem-fraction-static 0.85 --context-length 32768 \
    --speculative-algorithm EAGLE \
    --speculative-num-steps 3 --speculative-eagle-topk 1 \
    --speculative-num-draft-tokens 4 \
    --host 0.0.0.0 --port 30000
```

Target model load + KV pool + target CUDA graph all succeed. Crash is during draft worker init:

```
[TP0] Capture draft extend cuda graph begin (step 2). avail mem=12.08 GB
[TP0] Scheduler hit an exception: Traceback (most recent call last):
  File ".../scheduler.py", line 666, in maybe_init_draft_worker
    self.draft_worker = DraftWorkerClass(**draft_worker_kwargs)
  File ".../speculative/multi_layer_eagle_worker_v2.py", line 172, in __init__
    self.init_cuda_graphs()
  File ".../speculative/multi_layer_eagle_worker_v2.py", line 213, in init_cuda_graphs
    MultiLayerEagleMultiStepDraftExtendCudaGraphRunner(self)
  File ".../speculative/multi_layer_eagle_draft_extend_cuda_graph_runner.py", line 426, in run_once
    ret = self.model_runner.model.forward(
  File ".../models/mimo_v2_nextn.py", line 147, in forward
    hidden_states = self.self_attn(
  File ".../models/mimo_v2.py", line 597, in forward
    attn_output = self.attn(q, k, v, forward_batch, sinks=self.attention_sink_bias)
  File ".../layers/attention/triton_backend.py", line 949, in forward_extend
    self.extend_attention_fwd(
  File ".../layers/attention/triton_ops/extend_attention.py", line 617, in extend_attention_fwd
    _fwd_kernel[grid](
triton.compiler.errors.CompilationError: at 142:16:
        if not SKIP_TILE:
            offs_kv_loc = tl.load(
                kv_indices + cur_seq_kv_start_idx + start_n + offs_n,
                ^
AttributeError("'NoneType' object has no attribute 'type'")
```

### Root cause (best understanding)

- `mimo_v2_nextn.py` MTP blocks reuse `MiMoV2Attention` from `mimo_v2.py`, which is a **SWA layer** (`sliding_window=128`, `sinks=attention_sink_bias`).
- `MultiLayerEagleMultiStepDraftExtendCudaGraphRunner` step 1/2 builds a `forward_batch` with `kv_indices=None` (draft KV is in a contiguous temp buffer, not the paged KV pool).
- `triton_ops/extend_attention.py:_fwd_kernel` enters the `SLIDING_WINDOW_SIZE > 0` branch and unconditionally `tl.load(kv_indices + ...)` — there is no `kv_indices is None` guard for the "ragged extend without paged prefix" case when SWA is on.
- fa3/fa4 backends pass `page_table` instead and do not hit this codepath.

### Workarounds tried (all fail)

| Attempt | Result |
|---|---|
| Remove `--enable-multi-layer-eagle` | No effect — server auto-sets `enable_multi_layer_eagle=True` for MiMoV2 (`Enable multi-layer EAGLE speculative decoding for MiMoV2 model`) |
| `--speculative-attention-mode decode` | No effect — `MultiLayerEagleMultiStepDraftExtendCudaGraphRunner` still captures via `forward_extend` |
| `--speculative-draft-attention-backend fa4` | Not viable on SM120 (`flash_attn/cute/interface.py:870: Paged KV not supported on SM 12.0`) |

### Cross-check: same config **without** EAGLE works

Same image/hardware/flags minus the `--speculative-*` block: `/health` OK in 150s, GSM8K-style 5/5 correct, multimodal warmup passes with `--mm-attention-backend triton_attn`. So the triton backend itself handles MiMo's diffkv(192/128) + SWA + sink correctly for the target model — the bug is specific to the multi-layer draft extend path.

### Suggested fix direction

Either (a) make `extend_attention._fwd_kernel` skip the `kv_indices` load when it is `None` (no paged prefix to attend over in draft extend step≥1), or (b) have `MultiLayerEagleMultiStepDraftExtendCudaGraphRunner` populate a dummy `kv_indices` tensor for SWA layers when building the draft extend forward batch.

Happy to test a patch on the same SM120 setup.
