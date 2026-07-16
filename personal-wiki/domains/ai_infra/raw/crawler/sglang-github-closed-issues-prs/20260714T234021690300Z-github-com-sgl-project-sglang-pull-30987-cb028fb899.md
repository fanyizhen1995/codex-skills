---
source_id: sglang-github-closed-issues-prs
title: '[Bugfix] Fix DeepSeek ForwardFlags across custom op boundary'
canonical_url: https://github.com/sgl-project/sglang/pull/30987
captured_at: '2026-07-14T23:40:21.690300+00:00'
content_hash: cb028fb899419c640998d9acf8c99c0a3d91d55374811790e743788a74b83167
---
# [Bugfix] Fix DeepSeek ForwardFlags across custom op boundary

URL: https://github.com/sgl-project/sglang/pull/30987
State: closed
Labels: deepseek, run-ci, run-ci-extra
Closed at: 2026-07-14T00:19:44Z
Merged at: 2026-07-14T00:19:44Z

## Summary

#30802 caused the same `ForwardFlags` custom-op boundary bug that #30968 fixed for Nemotron, this time in DeepSeek's `tc_piecewise` dual-stream MoE path. We pass `fuse_mlp_allreduce` and `mlp_reduce_scatter` into the custom op and set them again inside.

## Accuracy

With `SGLANG_ENABLE_PCG_DSV2_DUAL_STREAM=1`, the fix improves the full 1,319-example single-shot GSM8K score by 3.11 percentage points, or 41 more correct answers.

| Metric | Before | After |
|---|---:|---:|
| Score | 92.49% | 95.60% |
| Stop rate | 96.82% | 99.01% |
| Truncated rate | 3.18% | 0.99% |
| Error rate | 0.00% | 0.00% |

```bash
sgl-eval run gsm8k \
  --base-url http://127.0.0.1:30000/v1 \
  --max-tokens 512 \
  --num-threads 512

# Before
gsm8k: 100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████| 1319/1319 [00:52<00:00, 24.98it/s, acc=92.49%]
== gsm8k ==
1319 examples (single-shot)  |  52.8s  |  5416 tok/s  |  286K tokens

* score           =  92.49%
  stop_rate       =  96.82%
  truncated_rate  =  3.18%  [warn: hitting max_tokens]
  error_rate      =  0.00%

# After
gsm8k: 100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████| 1319/1319 [00:43<00:00, 30.24it/s, acc=95.60%]
== gsm8k ==
1319 examples (single-shot)  |  43.6s  |  6406 tok/s  |  279K tokens

* score           =  95.60%
  stop_rate       =  99.01%
  truncated_rate  =  0.99%
  error_rate      =  0.00%
```

## Profiler

| Kernel | Before per TP rank | After per TP rank |
|---|---:|---:|
| `moe::dev::routing::routingDeepSeek::routingMainKernel` | 58 | 58 |
| `moe::dev::routing::routingDeepSeek::routingIndicesClusterKernel` | 58 | 58 |
| `moe::dev::finalize::finalizeKernelVecLoad` | 58 | 58 |
| `(anonymous namespace)::all_reduce_one_shot_kernel` | 59 | 2 |
| `flashinfer::trtllm_mnnvl_allreduce::twoshotAllreduceKernel` | 121 | 121 |
| `flashinfer::trtllm_mnnvl_allreduce::rmsNormLamport` | 121 | 121 |

The `all_reduce_one_shot_kernel` count drops from 59 to 2 per TP rank.





















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29230081489](https://github.com/sgl-project/sglang/actions/runs/29230081489)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #29230081352](https://github.com/sgl-project/sglang/actions/runs/29230081352)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
