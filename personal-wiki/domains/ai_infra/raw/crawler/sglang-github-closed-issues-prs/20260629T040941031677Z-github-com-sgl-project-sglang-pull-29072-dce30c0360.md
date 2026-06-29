---
source_id: sglang-github-closed-issues-prs
title: '[Cherry-pick to release/v0.5.14] Skip Flashinfer cuDNN FP8 GEMM tactic when
  cuDNN''s libcudart guard trips (#29071)'
canonical_url: https://github.com/sgl-project/sglang/pull/29072
captured_at: '2026-06-29T04:09:41.031677+00:00'
content_hash: dce30c0360a62d13b38f22df097600102690f47d78df9d84c4a7eb35094498fe
---
# [Cherry-pick to release/v0.5.14] Skip Flashinfer cuDNN FP8 GEMM tactic when cuDNN's libcudart guard trips (#29071)

URL: https://github.com/sgl-project/sglang/pull/29072
State: closed
Labels: 
Closed at: 2026-06-23T20:39:15Z
Merged at: 

Cherry-pick of #29071 to `release/v0.5.14`.

The fix is confirmed in the following run: https://github.com/sgl-project/sglang/pull/29064#issuecomment-4782398791

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

On Blackwell, ModelOpt FP8 linear goes through `bmm_fp8(backend="auto")`, so the Flashinfer autotuner probes the cuDNN FP8 GEMM tactic during warmup. When the image has both a CUDA 12 (torch) and CUDA 13 (cuda-tile) runtime mapped, cuDNN-frontend's shim throws while dlopen-ing libcudart:

```
RuntimeError: Multiple libcudart libraries found: libcudart.so.12 and libcudart.so.13
```

It's raised inside `CudnnFp8GemmRunner.get_valid_tactics`, which `AutoTuner.choose_one` doesn't guard, so it kills the scheduler during warmup. Nemotron-3-Super (`test_nvidia_nemotron_3_super_nvfp4` / `_nightly`) dies this way in nightly.

<!-- Describe the purpose and goals of this pull request. -->

## Modifications

Wrap Flashinfer's `_cudnn_gemm_fp8_runner` so tactic enumeration returns `[]` on that specific error → autotuner skips cuDNN and falls back to cutlass/cublas instead of crashing. Other errors re-raise, and healthy hosts (one libcudart) are untouched and still pick cuDNN.

The dual libcudart should really be fixed in the image — while both are mapped cuDNN can't resolve cudart at all (the failed scan isn't cached), so the tactic can't run there regardless.

<!-- Detail the changes made in this pull request. -->

## Accuracy Tests

No model output change — falls back to the existing cutlass/cublas FP8 path. Covered by the Nemotron-3-Super nightly tests.

## Speed Tests and Profiling

N/A, crash fix.

















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28048752452](https://github.com/sgl-project/sglang/actions/runs/28048752452)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28048748776](https://github.com/sgl-project/sglang/actions/runs/28048748776)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
