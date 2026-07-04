---
source_id: sglang-github-closed-issues-prs
title: '[XPU] Remove redundant xpu graph backend and make xpu graph opt-in by default'
canonical_url: https://github.com/sgl-project/sglang/pull/29911
captured_at: '2026-07-04T02:13:49.135852+00:00'
content_hash: 3e904e5def05dc4739b72af9e65eb860c8322f91a2dd450b4f8c683f373c51d2
---
# [XPU] Remove redundant xpu graph backend and make xpu graph opt-in by default

URL: https://github.com/sgl-project/sglang/pull/29911
State: closed
Labels: documentation, deepseek, intel, xpu, run-ci, diffusion
Closed at: 2026-07-03T07:58:57Z
Merged at: 2026-07-03T07:58:57Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Fix merge conflicts with https://github.com/sgl-project/sglang/pull/23180 and disable XPU Graph by default.

## Modifications

* Remove redundant xpu graph backend.
* Disable XPU Graph by default.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28638007192](https://github.com/sgl-project/sglang/actions/runs/28638007192)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28638007121](https://github.com/sgl-project/sglang/actions/runs/28638007121)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
