---
source_id: sglang-github-closed-issues-prs
title: '[NPU] Fix mrope_position computation in Eagle Worker v2 with PlanStream'
canonical_url: https://github.com/sgl-project/sglang/pull/23423
captured_at: '2026-06-29T04:09:41.026375+00:00'
content_hash: a9f36b2ec76a10cb96d1230d699fd26e84db3337e60c11ca3f5ca72151dbb2f6
---
# [NPU] Fix mrope_position computation in Eagle Worker v2 with PlanStream

URL: https://github.com/sgl-project/sglang/pull/23423
State: closed
Labels: npu, run-ci
Closed at: 2026-05-11T01:43:38Z
Merged at: 2026-05-11T01:43:37Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->
When SGLANG_ENABLE_SPEC_V2 and SGLANG_ENABLE_OVERLAP_PLAN_STREAM are enabled in multimodal scenarios, the Eagle Worker v2 computes mrope_position on the plan stream using draft outputs from the default stream. This race condition leads to incorrect mrope_position values.


## Modifications

<!-- Detail the changes made in this pull request. -->
Compute mrope_position on the default stream, and copy it to the graph buffer when CUDA graph is enabled.

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
