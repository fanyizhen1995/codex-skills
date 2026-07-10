---
source_id: sglang-github-closed-issues-prs
title: '[NPU] Fix NPU fallback for logits multimem all-gather'
canonical_url: https://github.com/sgl-project/sglang/pull/30668
captured_at: '2026-07-09T23:36:35.326763+00:00'
content_hash: f4ed9909866c45ceae88165b31f7f90e1484b7c00a3eefd5441c8ff6942a566b
---
# [NPU] Fix NPU fallback for logits multimem all-gather

URL: https://github.com/sgl-project/sglang/pull/30668
State: closed
Labels: 
Closed at: 2026-07-09T14:19:52Z
Merged at: 2026-07-09T14:19:52Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation
Running GLM-5.1/GLM-5.2 on NPU multi-node setups can fail during LogitsProcessor initialization after the logits multimem all-gather path was introduced.

The failure happens before fallback is reached:

RuntimeError: No backend type associated with device type npu
MultimemAllGatherer is a CUDA/NVIDIA-specific fast path. It relies on CUDA device APIs, symmetric memory, NVLink multicast, and Triton PTX multimem.st. However, its constructor currently performs the cross-node topology probe on all platforms. On NPU, this can enter in_the_same_node_as() and trigger a torch.distributed.all_reduce() with an NPU device/backend mismatch.
## Modifications

<!-- Detail the changes made in this pull request. -->

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29024559560](https://github.com/sgl-project/sglang/actions/runs/29024559560)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29024557668](https://github.com/sgl-project/sglang/actions/runs/29024557668)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
