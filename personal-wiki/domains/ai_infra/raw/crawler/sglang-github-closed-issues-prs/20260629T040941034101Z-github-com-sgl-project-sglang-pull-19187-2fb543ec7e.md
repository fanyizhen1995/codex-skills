---
source_id: sglang-github-closed-issues-prs
title: '[Feature] Enable EPLB in Draft Models'
canonical_url: https://github.com/sgl-project/sglang/pull/19187
captured_at: '2026-06-29T04:09:41.034101+00:00'
content_hash: 2fb543ec7e672972e67a486cf109ddd172fb3255a25d23bd131537fb929e1321
---
# [Feature] Enable EPLB in Draft Models

URL: https://github.com/sgl-project/sglang/pull/19187
State: closed
Labels: run-ci
Closed at: 2026-06-28T06:44:53Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

This resolves #7893 

## Modifications

Problem:
If draft expert count != target expert count:
- Incorrect `num_tokens_per_rank`
- Incorrect `_num_max_dispatch_tokens_per_rank`

Solution:  
- Expert-related parameters are now computed independently for target model and draft model, calculated per-model, based on model-specific `num_experts` and `model-specific ep_size`
- Updated dispatch capacity handling to accept model-specific token limits. Removed assumptions that `_num_max_dispatch_tokens_per_rank` is globally shared.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Benchmarking and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review Process

1. Ping Merge Oncalls to start the PR flow. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - `/tag-run-ci-label`, `/rerun-failed-ci`, `/tag-and-rerun-ci`
4. After green CI and required approvals, ask Merge Oncalls to merge.
