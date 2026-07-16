---
source_id: sglang-github-closed-issues-prs
title: '[AMD-miles] Bump miles rocm700-mi35x base image and migrate nightly test onto
  it'
canonical_url: https://github.com/sgl-project/sglang/pull/30587
captured_at: '2026-07-10T23:37:20.321497+00:00'
content_hash: e1b6cb16519429a19e46c273dc2c74ba3da1559b174e8f36a8a8c97f0501c689
---
# [AMD-miles] Bump miles rocm700-mi35x base image and migrate nightly test onto it

URL: https://github.com/sgl-project/sglang/pull/30587
State: closed
Labels: amd
Closed at: 2026-07-10T15:47:07Z
Merged at: 2026-07-10T15:47:07Z

Co-authored-with: @XinyuJiangCMU 
<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

The `rocm700-mi35x` image is the actively maintained miles ROCm image. This PR points it at the newer base image and moves the AMD miles nightly test onto `rocm700-mi35x` instead of `rocm720-mi35x`.

## Modifications

<!-- Detail the changes made in this pull request. -->

- Bump the `rocm700-mi35x` nightly image to the new `rocm/sgl-dev:v0.5.14-rocm700-mi35x-20260627` base.
- Add a `rocm700` nightly test workflow and remove the `rocm720-mi35x` one.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

N/A

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

N/A

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28990343363](https://github.com/sgl-project/sglang/actions/runs/28990343363)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28990343194](https://github.com/sgl-project/sglang/actions/runs/28990343194)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
