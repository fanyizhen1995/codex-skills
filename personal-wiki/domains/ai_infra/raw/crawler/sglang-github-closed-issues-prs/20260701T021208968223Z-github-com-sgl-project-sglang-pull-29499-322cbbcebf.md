---
source_id: sglang-github-closed-issues-prs
title: '[DSA] Optimize DSA CUDA graph replay metadata generation'
canonical_url: https://github.com/sgl-project/sglang/pull/29499
captured_at: '2026-07-01T02:12:08.968223+00:00'
content_hash: 322cbbcebff504810bdd89fa6c2453fef6fd06ba411f706ee3e266bf5a7d70ba
---
# [DSA] Optimize DSA CUDA graph replay metadata generation

URL: https://github.com/sgl-project/sglang/pull/29499
State: closed
Labels: run-ci, release-highlight
Closed at: 2026-06-30T02:53:24Z
Merged at: 2026-06-30T02:53:24Z

## Summary

This fuses the small DSA metadata work that runs right before CUDA graph replay. The main path is `_apply_cuda_graph_metadata`, where decode, target-verify, and draft-extend replay used to launch a bunch of small PyTorch metadata ops.

The new path uses fused Triton kernels for replay metadata generation and MTP replay precompute. It also refreshes DeepGEMM schedule metadata in place when the new DeepGEMM out API is available, with the old allocation-plus-copy path kept as fallback.

## Changes

- Fuse DSA decode, target-verify, and draft-extend-v2 metadata generation.
- Avoid runtime-length Triton recompiles with `do_not_specialize` on changing lengths and row strides.
- Fill target-verify `paged_mqa_ctx_lens_2d` inside the fused target-verify kernel, so there is no extra `expand().contiguous()` + copy path.
- Use a static-width draft-extend-v2 page-table path based on `speculative_num_draft_tokens`.
- Add `SGLANG_DSA_USE_FUSED_METADATA_GENERATION`, default enabled, with eager fallback if fused generation fails.

## Profile

Before: `glm-opt` upstream base

<img width="1253" height="392" alt="dsa-metadata-before-glm-opt-upstream-base" src="https://github.com/user-attachments/assets/252ff525-49ef-4e0c-8101-214b8fa00c83" />

After: fused DSA metadata generation + DeepGEMM schedule out API

<img width="1270" height="366" alt="dsa-metadata-after-fused-dsa-metadata" src="https://github.com/user-attachments/assets/0e1aaf7f-54be-4b59-936e-20996813f458" />

Profiled with the same GLM-5.2 NVFP4 TP4 EAGLE+DSA workload on GB300 (SM103) before and after this change.

| Range | Before | After | Improvement |
|---|---:|---:|---:|
| `_apply_cuda_graph_metadata` median | 885 us | 263 us | -622 us / 70.3% |
| `init_forward_metadata_out_graph` median | 796 us | 283 us | -513 us / 64.4% |
| `load_batch` median | 667 us | 330 us | -337 us / 50.5% |
| `_precompute_replay_metadata` median | 416 us | 178 us | -238 us / 57.2% |
| `eagle_prepare_for_verify` median | 1365 us | 658 us | -707 us / 51.8% |

The larger `run_batch` range also improved:

| Range | Before | After | Improvement |
|---|---:|---:|---:|
| `run_batch` median | 9155 us | 7112 us | -2043 us / 22.3% |

Memcpy direction counts did not add new CPU/GPU sync:

| Direction | Before | After | Change |
|---|---:|---:|---:|
| HtoD | 33 | 33 | unchanged |
| DtoH | 17 | 17 | unchanged |
| DtoD | 319 | 159 | -160 / 50.2% |
| `cudaMemcpyAsync` | 369 | 209 | -160 / 43.4% |

Small-op reductions:

| Event | Before | After | Reduction |
|---|---:|---:|---:|
| `aten::copy_` | 590 | 326 | -264 / 44.7% |
| `aten::cumsum` | 72 | 8 | -64 / 88.9% |
| `aten::repeat_interleave` | 24 | 8 | -16 / 66.7% |
| `aten::_to_copy` | 201 | 137 | -64 / 31.8% |
| `direct_copy` kernels | 246 | 142 | -104 / 42.3% |

## Check

- GLM-5.2 NVFP4, TP4, EAGLE, DSA, GB300 (SM103).
- GSM8K with `sgl-eval`: `97.12%` score, `100%` stop rate, `0%` error rate, `0%` truncated rate.
- Compared before/after SGLang profile traces collected with `sglang.bench_serving --profile` on the same generated shared-prefix workload.
- Verified no increase in HtoD/DtoH memcpy counts.
- Verified DSA fused metadata kernels show up in the after trace and the old small metadata ops are reduced.

## AIME 2025 Accuracy

```
== aime25 ==
30 examples x 16 repeats  |  1817.7s  |  5349 tok/s  |  9.7M tokens

* pass@1[avg-of-16]  =  91.88% +/- 4.71% (SEM 1.18%)
  pass@16            =  100.00%
  majority@16        =  96.67%
  no_answer          =  0.42%
  stop_rate          =  99.58%
  truncated_rate     =  0.42%
  error_rate         =  0.00%
```







































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28368325949](https://github.com/sgl-project/sglang/actions/runs/28368325949)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28417193617](https://github.com/sgl-project/sglang/actions/runs/28417193617)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
