---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] Support SP for Krea-2'
canonical_url: https://github.com/sgl-project/sglang/pull/29777
captured_at: '2026-07-08T23:36:33.802004+00:00'
content_hash: 05dce400f82f4752aa7ce9c70a4c5cce041ca69885b6f7427479ced1ac169874
---
# [diffusion] Support SP for Krea-2

URL: https://github.com/sgl-project/sglang/pull/29777
State: closed
Labels: documentation, run-ci, diffusion
Closed at: 2026-07-08T02:39:01Z
Merged at: 2026-07-08T02:39:01Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

**This PR depends on #29772; will rebase after it merges**

## Modifications

<!-- Detail the changes made in this pull request. -->

## Accuracy & Speed Tests

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

| Config | GPUs | warm e2e (s) | e2e speedup | denoise/step (s) | denoise speedup | decode (s) | MAE vs 1-GPU |
|---|---|---|---|---|---|---|---|
| baseline | 1 | 1.61 / 1.62 | 1.00× | 0.1725 / 0.1735 | 1.00× | 0.180 | — |
| **ulysses=2 (SP)** | 2 | 0.94 / 0.94 | **1.72×** | 0.1011 / 0.1012 | **1.71×** | 0.083 / 0.083 | **0.0000** |
| **tp=2** | 2 | 0.98 / 0.97 | **1.66×** | 0.1028 / 0.1030 | **1.68×** | 0.097 / 0.099 | 6.96 |
| **tp=2 × sp=2** | 4 | 0.58 / 0.58 | **2.78×** | 0.0602 / 0.0605 | **2.87×** | 0.047 | 6.96 *(= tp=2, bitwise)* |

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28465407911](https://github.com/sgl-project/sglang/actions/runs/28465407911)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28465407685](https://github.com/sgl-project/sglang/actions/runs/28465407685)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
