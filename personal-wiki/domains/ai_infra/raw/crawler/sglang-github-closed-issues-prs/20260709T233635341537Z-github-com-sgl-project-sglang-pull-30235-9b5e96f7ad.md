---
source_id: sglang-github-closed-issues-prs
title: '[Intel GPU] xpu_piecewise: fall back to eager when PCG capture stream is unset'
canonical_url: https://github.com/sgl-project/sglang/pull/30235
captured_at: '2026-07-09T23:36:35.341537+00:00'
content_hash: 9b5e96f7ad13461cbaad03a550141feb430e4686eca5f346ded477ecfda68b07
---
# [Intel GPU] xpu_piecewise: fall back to eager when PCG capture stream is unset

URL: https://github.com/sgl-project/sglang/pull/30235
State: closed
Labels: intel, xpu, run-ci, piecewise-cuda-graph
Closed at: 2026-07-09T02:21:44Z
Merged at: 2026-07-09T02:21:44Z

Mirror the HIP eager-fallback branch from CUDAPiecewiseBackend.__call__ in XPUPiecewiseBackend. When Dynamo silently recompiles a piecewise sub-graph for a token count outside the captured range (e.g. chunked prefill at 8192 tokens vs a capture grid topping out at 512), the recompiled backend has no capture stream. Previously this hit a bare assert and killed the prefill scheduler; now it degrades to eager for that sub-graph with a one-time warning, matching CUDA/HIP behavior.

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28916966921](https://github.com/sgl-project/sglang/actions/runs/28916966921)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28916966788](https://github.com/sgl-project/sglang/actions/runs/28916966788)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
