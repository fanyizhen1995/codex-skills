---
source_id: sglang-github-closed-issues-prs
title: '[NPU][bugfix] Fix NPU KernelLaunch Failure in rotate_input_ids_triton with
  Empty Batch'
canonical_url: https://github.com/sgl-project/sglang/pull/30589
captured_at: '2026-07-11T23:37:37.769505+00:00'
content_hash: b2684ec8b677d8a69b827e9e54221ae26245b0027dfc8a487c51bfc12331b12c
---
# [NPU][bugfix] Fix NPU KernelLaunch Failure in rotate_input_ids_triton with Empty Batch

URL: https://github.com/sgl-project/sglang/pull/30589
State: closed
Labels: npu, run-ci
Closed at: 2026-07-11T09:32:43Z
Merged at: 2026-07-11T09:32:43Z

## Motivation

This PR fixes an NPU runtime crash introduced by PR #28492 (Refactor / simplify MultiLayerEagleDraftExtendCudaGraphRunner to use rotation).
When extend_seq_lens has a batch size of 0 (e.g., a DP rank with no active requests), rotate_input_ids_triton launches a triton kernel with an empty grid. This violates NPU parameter verification rules and triggers the error:

> KernelLaunch failed because value 0 for parameter coreDim is invalid. Expected value: not equal to 0.

Root cause is confirmed via commit comparison: the issue does not exist on pre-PR commit bf231f01, and stably reproduces on merged commit 24bf8d91.

## Modifications

- Add an early return guard in rotate_input_ids_triton: when batch_size == 0, return input_ids directly without launching the kernel.
- This handles the empty batch edge case for DP ranks with no requests, and avoids invalid kernel launches on NPU platforms.

## Accuracy Tests

No accuracy impact. The fix only skips kernel execution for empty batches and does not alter behavior for valid inputs.

## Speed Tests and Profiling

No performance impact. The added boundary check has negligible overhead and only takes effect on empty batch scenarios.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29146698673](https://github.com/sgl-project/sglang/actions/runs/29146698673)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29146698670](https://github.com/sgl-project/sglang/actions/runs/29146698670)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
