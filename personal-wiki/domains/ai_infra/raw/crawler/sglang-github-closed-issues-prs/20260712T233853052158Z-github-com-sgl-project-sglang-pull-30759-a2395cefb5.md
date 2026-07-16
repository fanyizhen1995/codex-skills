---
source_id: sglang-github-closed-issues-prs
title: 'fix: allocate dspark target-verify buffers eagerly to avoid inference-tensor
  conflict'
canonical_url: https://github.com/sgl-project/sglang/pull/30759
captured_at: '2026-07-12T23:38:53.052158+00:00'
content_hash: a2395cefb59c37277555ceb5d06153fb5f262381204d8f14c243685efa0e75fe
---
# fix: allocate dspark target-verify buffers eagerly to avoid inference-tensor conflict

URL: https://github.com/sgl-project/sglang/pull/30759
State: closed
Labels: deepseek
Closed at: 2026-07-12T22:25:32Z
Merged at: 

## Motivation

DSPARK target-verify buffers (`extend_seq_lens_buffer`, `extend_start_loc_buffer`)
were lazy-allocated by `_ensure_verify_bs_buffers()` on first use. The first use
is the FlashInfer autotune `_dummy_run`, which wraps the forward inside
`torch.inference_mode()`. Tensors allocated there are tagged as inference
tensors, and subsequent CUDA-graph capture (outside inference_mode) fails with:

> Inplace update to inference tensor outside InferenceMode is not allowed.

## Modifications

- Allocate both buffers eagerly in `DeepseekV4AttnBackend.__init__` (runs
  outside inference_mode).
- Remove the now-unnecessary `_ensure_verify_bs_buffers` lazy-init method.

## Checklist

- [x] `pre-commit run --all-files`
- [x] Unit tests — N/A (pure bugfix, no behavioral change)
- [x] Documentation — N/A
- [x] Accuracy / Speed — N/A (no model output or performance impact)



















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29077340808](https://github.com/sgl-project/sglang/actions/runs/29077340808)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29077340909](https://github.com/sgl-project/sglang/actions/runs/29077340909)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
