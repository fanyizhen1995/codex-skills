---
source_id: sglang-github-closed-issues-prs
title: '[RL] fix deepseek v4 MXFP8 flashinfer_trtllm_routed MoE weight update'
canonical_url: https://github.com/sgl-project/sglang/pull/28676
captured_at: '2026-07-02T02:12:27.255565+00:00'
content_hash: acd7a8793cfd949327c4abf378086529436514ab1874b873248dfa956846febf
---
# [RL] fix deepseek v4 MXFP8 flashinfer_trtllm_routed MoE weight update

URL: https://github.com/sgl-project/sglang/pull/28676
State: closed
Labels: 
Closed at: 2026-07-01T19:29:09Z
Merged at: 2026-07-01T19:29:09Z

## Motivation

DeepSeek-V4 (MXFP8) on the `flashinfer_trtllm_routed` MoE path breaks after the
first RL weight update: `train_rollout_logprob_abs_diff` jumps from ~0.06 to
**~3.83**. Steady-state is fine — the bug is specific to the weight-reload path.

## Root cause

`align_mxfp8_moe_weights_for_flashinfer_trtllm` shuffles MoE weights/scales into
the kernel layout using row-permutation index tensors that depend only on shape,
so they're memoized in the GPU cache `_flashinfer_trtllm_shuffle_row_indices_cache_mxfp8`
(added in #21280).

These cached index tensors are GPU-resident and live in the pauseable weights memory region. On a weight update sglang releases that region's physical memory on pause and reallocates it on resume; since the cache is a plain module global outside the saved/restored static state, its tensors are left pointing at stale memory. We drop it so the indices get recomputed. 

The cachestill hits (same shape) but the contents are now garbage, so the post-update
`align` permutes the new weights with stale indices → corrupted layout → the 3.83
blowup. Affects any FP8 MoE on the flashinfer-trtllm path that goes through a
weight update, not just V4.

## Changes

1. **Bug fix** — add `clear_mxfp8_shuffle_index_cache()` in `flashinfer_trtllm.py`
   and call it from the weight-load funnel in `fused_moe_triton/layer.py`
   (`_weight_loader_impl` + `weight_loader_fused`, gated on `Fp8MoEMethod`). This
   funnel covers both the colocate and distributed/EP update paths, so the next
   `align` recomputes correct indices after any reload.
2. **V4 enablement** — implement `apply_routed_scaling_factor_on_output` in
   `hash_topk.py` (store the flag, drop the `not implemented` assert, apply
   `topk_weights *= routed_scaling_factor` in `forward`), as required by the
   routed kernel.

## Testing

5-step Pinaster/DeepSeek-V4-Flash-FP8-4layer MXFP8 RL run (weight update before each step):

| step | 0 | 1 | 2 | 3 | 4 |
|------|------|------|------|------|------|
| `train_rollout_logprob_abs_diff` | 0.069 | 0.062 | 0.068 | 0.065 | 0.062 |

All steps healthy (~0.06), no 3.83 blowup.

















































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28472150683](https://github.com/sgl-project/sglang/actions/runs/28472150683)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28472150366](https://github.com/sgl-project/sglang/actions/runs/28472150366)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
