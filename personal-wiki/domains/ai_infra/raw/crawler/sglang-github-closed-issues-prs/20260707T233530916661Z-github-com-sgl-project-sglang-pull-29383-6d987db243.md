---
source_id: sglang-github-closed-issues-prs
title: 'feat(sgl-kernel): add InfLLM v2 attention kernels'
canonical_url: https://github.com/sgl-project/sglang/pull/29383
captured_at: '2026-07-07T23:35:30.916661+00:00'
content_hash: 6d987db24395efb04fc876c655d5130da679666852a08df62eebfee14290f083
---
# feat(sgl-kernel): add InfLLM v2 attention kernels

URL: https://github.com/sgl-project/sglang/pull/29383
State: closed
Labels: sgl-kernel, run-ci
Closed at: 2026-07-07T05:46:54Z
Merged at: 2026-07-07T05:46:54Z

Add InfLLM v2 sparse attention stage1 and max pooling CUDA kernels with Python bindings under sgl-kernel/python/sgl_kernel/infllm_v2/.

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

This PR adds standalone `sgl-kernel` support for the InfLLM v2 sparse attention primitives. The new kernels expose the stage1 sparse attention score computation and the variable-length max pooling step through `sgl_kernel`, so downstream SGLang model code can call them without depending on the separate third-party InfLLM v2 CUDA extension.

## Modifications

- Add InfLLM v2 FlashAttention-style CUDA sources for varlen stage1 sparse attention under `sgl-kernel/csrc/infllm_v2/flash_attn/`.
- Add the InfLLM v2 variable-length 1D max pooling CUDA kernel in `sgl-kernel/csrc/infllm_v2/max_pooling.cu`.
- Register the new extension entry points in `sgl-kernel/CMakeLists.txt`, `sgl-kernel/csrc/common_extension.cc`, and `sgl-kernel/include/sgl_kernel_ops.h`.
- Add Python bindings and lazy loading under `sgl-kernel/python/sgl_kernel/infllm_v2/`, exporting:
  - `infllmv2_attn_stage1`
  - `max_pooling_1d_varlen`
- Add CUDA tests for the stage1 attention binding and max pooling binding.
- Update the codespell allowlist for InfLLM-related names.

## Accuracy Tests

Added unit tests:

- `sgl-kernel/tests/test_infllm_v2_attention.py` compares `sgl_kernel.infllm_v2.infllmv2_attn_stage1` against the reference `infllm_v2` package (<https://github.com/OpenBMB/infllmv2_cuda_impl>) for BF16 inputs, head dimensions 64 and 128, causal and non-causal modes, and multiple sequence lengths.
- `sgl-kernel/tests/test_infllm_v2_max_pooling.py` compares `max_pooling_1d_varlen` against a pure PyTorch reference across FP16/BF16, multiple head counts, and variable-length batches.

## Speed Tests and Profiling

This PR adds the kernel implementation and bindings; end-to-end speed benchmarking should be done with the downstream model integration that consumes these primitives.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.

































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28842483694](https://github.com/sgl-project/sglang/actions/runs/28842483694)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28842483565](https://github.com/sgl-project/sglang/actions/runs/28842483565)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
