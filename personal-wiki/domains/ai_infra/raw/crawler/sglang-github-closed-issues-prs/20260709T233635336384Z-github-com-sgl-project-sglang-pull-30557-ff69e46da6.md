---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Fix AITER custom all-gather CUDA-graph capture crash under torch_memory_saver'
canonical_url: https://github.com/sgl-project/sglang/pull/30557
captured_at: '2026-07-09T23:36:35.336384+00:00'
content_hash: ff69e46da636ed95917a271e369380a18704c006603b5746b28d86211dc9115c
---
# [AMD] Fix AITER custom all-gather CUDA-graph capture crash under torch_memory_saver

URL: https://github.com/sgl-project/sglang/pull/30557
State: closed
Labels: 
Closed at: 2026-07-09T08:30:52Z
Merged at: 2026-07-09T08:30:52Z

Co-authored-with: @XinyuJiangCMU 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

On ROCm, the AITER custom all-gather calls `all_gather_reg` during CUDA-graph capture. When the CUDA-graph memory pool is managed by `torch_memory_saver`, that buffer is a HIP VMM allocation, and registering it via `hipIpcGetMemHandle` fails at capture end and aborts the process.

This is the same conflict already handled for custom all-reduce in [#19162](https://github.com/sgl-project/sglang/pull/19162) and [#20155](https://github.com/sgl-project/sglang/pull/20155) (also ROCm/aiter [#2075](https://github.com/ROCm/aiter/pull/2075)).

## Modifications

<!-- Detail the changes made in this pull request. -->

In `GroupCoordinator._all_gather_into_tensor`, gate the full-graph capture branch on `SGLANG_MEMORY_SAVER_CUDA_GRAPH`: use `all_gather_unreg` when `torch_memory_saver` is active. Behavior is unchanged when `torch_memory_saver` is disabled.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

Verified end-to-end with Miles on MI355X / ROCm 7.0 using a colocated setup.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28968253427](https://github.com/sgl-project/sglang/actions/runs/28968253427)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28968252920](https://github.com/sgl-project/sglang/actions/runs/28968252920)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
