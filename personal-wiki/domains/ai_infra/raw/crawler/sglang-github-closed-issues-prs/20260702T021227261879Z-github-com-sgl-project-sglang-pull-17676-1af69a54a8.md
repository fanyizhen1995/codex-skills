---
source_id: sglang-github-closed-issues-prs
title: '[NPU]fix eplb with nz'
canonical_url: https://github.com/sgl-project/sglang/pull/17676
captured_at: '2026-07-02T02:12:27.261879+00:00'
content_hash: 1af69a54a88f282eb90154cd2b05cb68495cb277aff676f84e6ae686b4b70218
---
# [NPU]fix eplb with nz

URL: https://github.com/sgl-project/sglang/pull/17676
State: closed
Labels: npu, run-ci
Closed at: 2026-07-01T09:07:26Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

fix eplb error when weight format type is ACL_FORMAT_FRACTAL_NZ

<!-- Describe the purpose and goals of this pull request. -->

## Modifications

<!-- Detail the changes made in this pull request. -->

replace the big nz tensor with List<nz_tensor>

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

error before fix

<img width="951" height="122" alt="image" src="https://github.com/user-attachments/assets/18e94c31-a260-4882-8c5a-e6d8401506a8" />

accuracy after fix

<img width="794" height="187" alt="image" src="https://github.com/user-attachments/assets/a0e92b90-b163-4325-99b2-a76a56169282" />


## Benchmarking and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review Process

1. Ping Merge Oncalls to start the PR flow. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - `/tag-run-ci-label`, `/rerun-failed-ci`, `/tag-and-rerun-ci`
4. After green CI and required approvals, ask Merge Oncalls to merge.
