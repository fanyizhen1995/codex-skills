---
source_id: sglang-github-closed-issues-prs
title: '[sglang-miles] Cherry-pick #28371: [LoRA] Fix chunked SGMV (csgmv) CUDA graph
  segment replay'
canonical_url: https://github.com/sgl-project/sglang/pull/29872
captured_at: '2026-07-02T02:12:27.252599+00:00'
content_hash: 5d43d9a9b10b1a75e0ba8de1179c8b61cc9be5d6eeeab323f9bb49c054f2b5a4
---
# [sglang-miles] Cherry-pick #28371: [LoRA] Fix chunked SGMV (csgmv) CUDA graph segment replay

URL: https://github.com/sgl-project/sglang/pull/29872
State: closed
Labels: lora
Closed at: 2026-07-01T22:09:32Z
Merged at: 2026-07-01T22:09:32Z

Cherry-pick of #28371 (commit `093908d4c0df80453e89e873f721b9830c857742`, on `main`) onto `sglang-miles`.

Re-applies the fix after the earlier merge (#28499) was dropped when `sglang-miles` was rebuilt on a newer base. The buggy pattern is still present on the current branch (`chunked_sgmv_shrink.py`: `batch_info.bs if batch_info.use_cuda_graph else num_segments`), so the fix is still needed.

## What it fixes
In CUDA-graph mode the chunked-SGMV (csgmv) LoRA kernels baked the grid size (`batch_info.bs`) and the `num_segments` scalar into the captured graph at capture time. On replay the real batch's segment count differs, so the kernels processed the wrong number of segments — dropping the LoRA delta for some segments, or reading stale tail metadata that covers live token rows. csgmv is the default LoRA backend, so any multi-adapter decode batch under CUDA graph was affected.

The fix makes the grid and `num_segments` a capture-invariant value (the statically-sized buffer `weight_indices.shape[0]`) and neutralizes the unused tail every step in `prepare_lora_batch` (`weight_indices[num_segments:].zero_()`, `seg_indptr[num_segments+1:].fill_(total_tokens)`) so padded segments are zero-length and skipped via an added `seg_start == seg_end` early-exit. The same baked-scalar fix is applied to the absorbed-MLA `kv_b` LoRA kernels.

## Notes
- Clean cherry-pick — all 7 files apply without conflict on the current base (unlike the first attempt, `trtllm_lora_temp/` exists here so nothing is dropped).
- Validated on GB300: the 4 new CUDA-graph unit tests pass and the full `test_chunked_sgmv_backend.py` is green (16 passed / 39 subtests).

7 files changed, +392/−27.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28550757620](https://github.com/sgl-project/sglang/actions/runs/28550757620)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28550757447](https://github.com/sgl-project/sglang/actions/runs/28550757447)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
