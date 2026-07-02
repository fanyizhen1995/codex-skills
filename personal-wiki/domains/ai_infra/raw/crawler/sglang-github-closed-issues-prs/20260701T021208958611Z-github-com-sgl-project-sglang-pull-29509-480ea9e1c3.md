---
source_id: sglang-github-closed-issues-prs
title: '[NPU]GLM-4.7-Flash optimize with fused kernels'
canonical_url: https://github.com/sgl-project/sglang/pull/29509
captured_at: '2026-07-01T02:12:08.958611+00:00'
content_hash: 480ea9e1c32d94dac93bb46bad3ad25444edea71686b866feeca30a596a0730d
---
# [NPU]GLM-4.7-Flash optimize with fused kernels

URL: https://github.com/sgl-project/sglang/pull/29509
State: closed
Labels: deepseek, npu, run-ci
Closed at: 2026-06-30T11:22:20Z
Merged at: 2026-06-30T11:22:20Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Introduce a fused Triton kernel to improve model performance.

## Modifications

Replace the original split + RMSNorm pipeline with a fused Triton kernel.
<!-- Detail the changes made in this pull request. -->

## Accuracy Tests
Before:
<img width="667" height="86" alt="image" src="https://github.com/user-attachments/assets/68ae017c-fc6a-4484-9178-72478019a71b" />
After:
<img width="662" height="85" alt="image" src="https://github.com/user-attachments/assets/3ab4c852-71fe-4ecb-8915-f252769b1f9e" />

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling
<img width="631" height="491" alt="屏幕截图 2026-06-27 184820" src="https://github.com/user-attachments/assets/9d0ea45f-dc96-46db-bd5d-e856d736a5a4" />

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28347519019](https://github.com/sgl-project/sglang/actions/runs/28347519019)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28347518980](https://github.com/sgl-project/sglang/actions/runs/28347518980)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
