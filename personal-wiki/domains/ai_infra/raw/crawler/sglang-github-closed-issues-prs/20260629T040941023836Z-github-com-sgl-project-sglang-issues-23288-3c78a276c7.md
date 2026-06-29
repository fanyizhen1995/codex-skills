---
source_id: sglang-github-closed-issues-prs
title: '[HiSparse][ROCm] page_size + TP-collective deadlock + GPU memory fault on
  MI355X with GLM-5-FP8 (6 issues, 2 PR branches ready)'
canonical_url: https://github.com/sgl-project/sglang/issues/23288
captured_at: '2026-06-29T04:09:41.023836+00:00'
content_hash: 3c78a276c75cb73d5358a9f73c5100179e4a1ab49c1a50ce71fc002a0430dfde
---
# [HiSparse][ROCm] page_size + TP-collective deadlock + GPU memory fault on MI355X with GLM-5-FP8 (6 issues, 2 PR branches ready)

URL: https://github.com/sgl-project/sglang/issues/23288
State: closed
Labels: high priority, inactive
Closed at: 2026-06-29T00:51:19Z
Merged at: 

## Summary

`--enable-hisparse` is currently non-functional on AMD ROCm (tested on MI355X / gfx950). We have identified 6 distinct issues blocking it and have draft fixes for several, but the remaining issues need help from the HiSparse maintainers (cc @hzh0425, @xiezhq-hermann, @hnyls2002, @wufann, @huangtingwei9988) to land cleanly upstream.

This issue documents the full investigation, working PR branches, the AITER-side blocker, and a clear request for review.

## Environment

- **Hardware**: 8x MI355X (gfx950), Tensorwave amd-aim partition
- **Image**: `lmsysorg/sglang:v0.5.10.post1-rocm720-mi35x`
- **Model**: GLM-5-FP8 (`zai-org/GLM-5-FP8`-style, 64 attention heads / 8 KV heads / 384 experts / 6144 hidden / 48 MoE layers)
- **Server config**: `--tp 8 --enable-hisparse --hisparse-config '{"top_k": 2048, "device_buffer_size": 2048, "host_to_device_ratio": 1}' --nsa-prefill-backend aiter --nsa-decode-backend aiter --kv-cache-dtype bfloat16 --mem-fraction-static 0.65 --disable-cuda-graph --disable-radix-cache --skip-server-warmup`
- AITER `0.1.11.post2.dev0+g417de6df4`

## Reproducer

```bash
# in lmsysorg/sglang:v0.5.10.post1-rocm720-mi35x container
HISPARSE_CFG='{"top_k": 2048, "device_buffer_size": 2048, "host_to_device_ratio": 1}'

python3 -m sglang.launch_server \
    --model-path <GLM-5-FP8> --tp 8 --port 8000 \
    --trust-remote-code \
    --tool-call-parser glm47 --reasoning-parser glm45 \
    --mem-fraction-static 0.65 \
    --enable-hisparse --hisparse-config "$HISPARSE_CFG" \
    --disable-radix-cache \
    --nsa-prefill-backend aiter --nsa-decode-backend aiter \
    --kv-cache-dtype bfloat16 \
    --max-running-requests 256 --disable-cuda-graph --watchdog-timeout 1200 --skip-server-warmup
```

Without any patches, this fails immediately on `assert self.page_size == 1` in `NSATokenToKVPool.__init__`. Each fix below is required to get further.

---

## Issues found, in order of discovery

### Issue 1 — `NSATokenToKVPool` and `HiSparseAllocator` have mutually exclusive page_size assumptions on HIP

* `python/sglang/srt/server_args.py:1577` forces `page_size=1` on HIP for DSA models.
* `python/sglang/srt/mem_cache/memory_pool.py:1853` asserts `page_size == 1` on HIP, `page_size == 64` on CUDA.
* `python/sglang/srt/mem_cache/hisparse_memory_pool.py:191`/`275` requires `page_size > 1`.

→ HiSparse cannot run on HIP because the page_size required by the allocator is rejected by the pool.

**Fix branch**: https://github.com/andyluo7/sglang/tree/hisparse-rocm-page-size-fix

* `server_args.py`: only force `page_size=1` on HIP when HiSparse is OFF.
* `memory_pool.py`: relax assertion to `page_size in (1, 64)`. Note the `index_k_with_scale_buffer` layout is *already* parametric in `page_size` (line 1872), so no buffer-shape change is needed.
* `index_buf_accessor.py`: parametrize `buf_numel_per_page` check on `page_size`, drop per-platform asserts.
* `nsa_indexer.py`: pick `get_page_table_1()` vs `get_page_table_64()` based on runtime `page_size` rather than `is_hip()`.

Tested: with this patch, `--enable-hisparse` boots past the page_size assertion and reaches AITER decode kernel selection.

### Issue 2 — AITER `mla_decode_stage1_asm_fwd` has no `gqa_ratio=8` kernels

GLM-5 on TP=8 produces gqa_ratio=8 (64 attn heads / 8 KV heads / 8 ranks = 1 KV head per rank, 8 attn heads). AITER's `cfg_mla_asm` table only has gqa ∈ {16, 32, 64, 128}.

```
RuntimeError: get_heuristic_kernel_mla: cannot get heuristic kernel!
  q_type:bf16 kv_type:bf16 gqa:8 ps:0 prefill:0 causal:0 qseqlen:1
```

**AITER issue filed**: https://github.com/ROCm/aiter/issues/2821

**Workaround**: Existing upstream commit [`19cb91865`](https://github.com/sgl-project/sglang/commit/19cb91865) ([Not-Merge][AMD] GLM-5 performance optimization, by @wufann) pads heads 8 → 16 via `repeat_interleave`. Works for GLM-5 specifically. Should probably land properly (it's currently `[Not-Merge]`).

### Issue 3 — `nsa_indexer.py:433` hardcodes `block_kv = 1` on HIP

```python
block_kv = 1 if _is_hip else 64
```

When HiSparse is enabled and page_size is forced to 64 on HIP (Issue 1 fix), the `deepgemm_fp8_paged_mqa_logits` call passes `KVBlockSize=block_kv=1` while `block_tables` is from `get_page_table_64()`. Mismatch → kernel walks past valid memory.

**Fix**: change to `block_kv = page_size` (included in our local patch).

### Issue 4 — `host_to_device_ratio: 8` defaults are NVIDIA-tuned

Default requests host RAM = 8 × per-TP KV size. On TP=8 / GLM-5 / MI355X with ~89 GB/TP, that's 5.7 TB host RAM, exceeding typical 3 TB box. Some TPs allocate, others fail silently → `HIP error: invalid argument` deferred to next GPU op.

**Fix**: set `host_to_device_ratio: 1` (89 GB host/TP, total ~712 GB, fits). Should be a runtime check + actionable error in `hisparse_coordinator.py`.

### Issue 5 — `collect_ready_reqs()` deadlocks on HIP under TP

After Issues 1–4 are addressed, `_forward_aiter_extend` runs and prefill completes (we measured ~9516 tok/s on a single batch). Then a different rank (e.g., TP4) hangs in:

```
File "hisparse_coordinator.py", line 264, in collect_ready_reqs
File "torch/distributed/distributed_c10d.py", line 2942, in all_reduce
```

**Root cause**: `collect_ready_reqs` early-returns when `len(self.ack_staging_queue) == 0` *before* calling the all_reduce that synchronizes queue size across ranks. HiSparse top-k is per-rank (each rank has different sharded heads), so the staging queue length can legitimately differ across ranks. One rank early-returns and proceeds to the next forward-pass collectives; another enters the staging all_reduce and waits forever for peers that have moved on. NCCL/RCCL ordering deadlock until watchdog SIGABRTs.

On CUDA this rarely surfaces because `cudaEvent.query()` resolves fast enough that ranks usually agree. On HIP the timing variance in `hipEvent.query()` exposes it reliably.

**Fix branch**: https://github.com/andyluo7/sglang/tree/hisparse-rocm-tp-collective-sync — gates the early-return on a TP-collective MAX all_reduce of `len(queue) > 0`, so all ranks agree to enter or skip the subsequent all_reduce together.

### Issue 6 — GPU memory access faults during prefill, even after Issues 1–5

After all the above fixes, the very first prefill batch produces:

```
Memory access fault by GPU node-N (Agent handle: 0x...) on address 0x...da000. Reason: Unknown.
```

on all 8 ranks simultaneously. Address suffixes are correlated (`...bda000` / `...dfda000`), suggesting same OOB type.

* The fault does NOT occur without HiSparse on the same model/server config (the AITER NSA backend without `--enable-hisparse` runs cleanly at 2980 tok/s @ conc=128).
* The fault DOES occur with our PyTorch fallback for `load_cache_to_device_buffer_mla` (PR2 in the proposal) AND with a complete no-op fallback. So our fallback is not the source.
* Adding `torch.cuda.synchronize()` after `swap_in_selected_pages` and immediately before `mla_decode_fwd` does NOT prevent it.
* Adding instrumentation prints (which include `.item()` host syncs) on `page_table_1` makes a single prefill batch succeed (likely racing the bug), but it returns on subsequent batches.

**This is the remaining blocker.** We don't have enough internal context on the HiSparse coordinator's GPU-side invariants to localize it further. Likely candidates:

1. `swap_in_selected_pages` returns indices that are still being written by an async kernel; subsequent `_forward_aiter_extend` reads `page_table_1` too early.
2. Some Triton kernel inside the indexer / `transform_index_page_table_*` writes past valid memory under HIP.
3. The HiSparse coordinator's per-rank state divergence (Issue 5) leaves `device_buffer_tokens` in an inconsistent state that the JIT kernel reads.

We've filed the AITER-side missing-kernel issue (https://github.com/ROCm/aiter/issues/2821) and have working PRs for Issues 1, 5. Issues 2, 3, 4 have local fixes ready to upstream once we know the right way to gate them. Issue 6 needs HiSparse maintainer help.

---

## Patches and branches

| Branch | Issue | Status |
|---|---|---|
| https://github.com/andyluo7/sglang/tree/hisparse-rocm-page-size-fix | Issue 1 | Ready to PR |
| https://github.com/andyluo7/sglang/tree/hisparse-rocm-tp-collective-sync | Issue 5 | Ready to PR |
| https://github.com/ROCm/aiter/issues/2821 | Issue 2 | Filed, awaiting kernel work |
| (local) `block_kv = page_size` in nsa_indexer.py | Issue 3 | Will include in PR-1 |
| (local) `host_to_device_ratio` HIP default | Issue 4 | Small follow-up |

## Asks

1. **HiSparse maintainers**: Could @hzh0425, @xiezhq-hermann, or @hnyls2002 review the design intent of `collect_ready_reqs` and confirm whether the per-rank early-return is intentional? Our fix (TP-collective MAX gate) should be safe but we may be missing context.
2. **HIP / GPU sync**: Could you suggest where the prefill GPU fault might originate? Is there a synchronization point we're missing between `swap_in_selected_pages` and `_forward_aiter_extend`?
3. **PR-1 review**: We'd like to open the page_size fix as a draft PR. Any objections to the approach (`page_size in (1, 64)` allowed, with HiSparse forcing 64 on HIP)?
4. **AMD GLM-5 path**: Should the `[Not-Merge]` head-padding commit (`19cb91865` by @wufann) be promoted to merge? It's load-bearing for any GLM-5-on-AMD path.

We're happy to do the work; we just need the design hints. Thank you for the very active development on HiSparse — it's clearly the future of long-context serving.

---

cc @hzh0425 @xiezhq-hermann @hnyls2002 @wufann @huangtingwei9988 @whybeyoung
