---
source_id: sglang-github-closed-issues-prs
title: '[NPU] bugfix for dsv4 memory pool'
canonical_url: https://github.com/sgl-project/sglang/pull/30001
captured_at: '2026-07-04T02:13:49.134602+00:00'
content_hash: 7cfb5884e92b74dfaa8b102b554fab07cfdc9c6db55c12371f6a3b3c6f7f3322
---
# [NPU] bugfix for dsv4 memory pool

URL: https://github.com/sgl-project/sglang/pull/30001
State: closed
Labels: run-ci
Closed at: 2026-07-03T08:41:40Z
Merged at: 2026-07-03T08:41:40Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Since https://github.com/sgl-project/sglang/pull/28612 introduced `clear_unaccepted_c128_draft_states`, this functionality also needs to be implemented on NPU, even though no actual cleanup is required there.

<!-- Describe the purpose and goals of this pull request. -->

## Modifications

<!-- Detail the changes made in this pull request. -->

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

```
┌───────────────────────────────┬──────────────┬──────────┬──────────┬───────┬─────────┬─────────┐
│ Model                         │ Dataset      │ Metric   │ Subset   │   Num │   Score │ Cat.0   │
├───────────────────────────────┼──────────────┼──────────┼──────────┼───────┼─────────┼─────────┤
│ DeepSeek-V4-Flash-w8a8-mtp-ms │ gpqa_diamond │ mean_acc │ default  │   198 │  0.7231 │ default │
└───────────────────────────────┴──────────────┴──────────┴──────────┴───────┴─────────┴─────────┘
```
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28636613681](https://github.com/sgl-project/sglang/actions/runs/28636613681)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28636613592](https://github.com/sgl-project/sglang/actions/runs/28636613592)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
