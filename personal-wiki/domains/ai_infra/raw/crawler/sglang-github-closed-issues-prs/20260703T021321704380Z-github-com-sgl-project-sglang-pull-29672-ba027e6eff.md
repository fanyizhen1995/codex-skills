---
source_id: sglang-github-closed-issues-prs
title: '[amd][diffusion] Fix causal Conv3D cat/pad fusion crashes for wan2.2 t2v'
canonical_url: https://github.com/sgl-project/sglang/pull/29672
captured_at: '2026-07-03T02:13:21.704380+00:00'
content_hash: ba027e6eff2497efa3b7ff4cdd9bde4ccf1cdb14305c47d8ce2e7901db6ecfa3
---
# [amd][diffusion] Fix causal Conv3D cat/pad fusion crashes for wan2.2 t2v

URL: https://github.com/sgl-project/sglang/pull/29672
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-02T05:11:30Z
Merged at: 2026-07-02T05:11:30Z


## Motivation

`_can_fuse_causal_conv3d_cat_pad` decides whether to use the fused CUDA/Triton causal-conv3d cat/pad kernels. Those kernels are imported only under `current_platform.is_cuda()`, so on ROCm both `fused_causal_conv3d_cat_pad_cuda` and `fused_causal_conv3d_cat_pad_triton` are `None`.

However, eligibility was gated on `x.is_cuda`, which is `True` for ROCm/HIP tensors. As a result `_can_fuse_...` returns `True` on ROCm for padded convs, `causal_conv3d_cat_pad` then calls `fused_causal_conv3d_cat_pad`, and the wrapper raises:

    RuntimeError: causal Conv3D cat/pad fusion is only available on CUDA

This makes VAE decode (e.g. Wan2.2 T2V) fail on ROCm.

## Modifications

Gate eligibility on `current_platform.is_cuda()` so ROCm falls back to the existing `torch.cat` + `F.pad` path in `causal_conv3d_cat_pad`. No behavior change on CUDA.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.



































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28428205652](https://github.com/sgl-project/sglang/actions/runs/28428205652)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28428205598](https://github.com/sgl-project/sglang/actions/runs/28428205598)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
