---
source_id: sglang-github-closed-issues-prs
title: '[NPU] Fix block_table batch size mismatch in GLM-4.7-Flash DeepEP + MTP without
  CUDA Graphs'
canonical_url: https://github.com/sgl-project/sglang/pull/29829
captured_at: '2026-07-03T02:13:21.707349+00:00'
content_hash: 6b0dc4d546b3442395bec497bb796266af2ca270e57f9d0632435c79b4f986a8
---
# [NPU] Fix block_table batch size mismatch in GLM-4.7-Flash DeepEP + MTP without CUDA Graphs

URL: https://github.com/sgl-project/sglang/pull/29829
State: closed
Labels: npu, run-ci
Closed at: 2026-07-02T03:09:02Z
Merged at: 2026-07-02T03:09:02Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

When CUDA Graphs are disabled, enabling DeepEP together with MTP causes a batch size mismatch between the block table and the query.

## Modifications

In forward_mtp, when CUDA Graphs are disabled, slice the block table and actual_seq_lengths_kv to the actual batch size so that their first dimension matches the query batch size. This prevents batch size mismatches when DeepEP is used together with MTP.

## Accuracy Tests

<img width="2302" height="124" alt="image" src="https://github.com/user-attachments/assets/653a6bd1-0621-4871-9d5b-b0885ee60157" />

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28503725928](https://github.com/sgl-project/sglang/actions/runs/28503725928)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28503725600](https://github.com/sgl-project/sglang/actions/runs/28503725600)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
