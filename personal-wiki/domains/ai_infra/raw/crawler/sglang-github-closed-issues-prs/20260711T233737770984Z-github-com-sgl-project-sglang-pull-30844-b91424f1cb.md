---
source_id: sglang-github-closed-issues-prs
title: 'bugfix: add NPU to send_first check to prevent PP ring deadlock'
canonical_url: https://github.com/sgl-project/sglang/pull/30844
captured_at: '2026-07-11T23:37:37.770984+00:00'
content_hash: b91424f1cb59a7c986c1369449dd454bd7d9698df28f24cc3f9d896bcd3a0b59
---
# bugfix: add NPU to send_first check to prevent PP ring deadlock

URL: https://github.com/sgl-project/sglang/pull/30844
State: closed
Labels: 
Closed at: 2026-07-11T07:27:08Z
Merged at: 2026-07-11T07:27:08Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

HCCL's HcclSend uses synchronous calling mode (blocks the stream until a matching HcclRecv is posted), unlike CUDA/NCCL where isend is asynchronous. The existing send_first parity check only covered XPU, leaving NPU ranks all sending first simultaneously, causing a circular wait deadlock when TP>1 and PP>1.

## Modifications

<!-- Detail the changes made in this pull request. -->

python/sglang/srt/managers/scheduler_pp_mixin.py

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

NA

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

NA

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29143695279](https://github.com/sgl-project/sglang/actions/runs/29143695279)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29143695204](https://github.com/sgl-project/sglang/actions/runs/29143695204)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
