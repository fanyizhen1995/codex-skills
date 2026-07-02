---
source_id: sglang-github-closed-issues-prs
title: '[fix] Add support for flashinfer MOE A2A to Qwen3 BF16 model path'
canonical_url: https://github.com/sgl-project/sglang/pull/26255
captured_at: '2026-07-02T02:12:27.262144+00:00'
content_hash: 0079c35ec30b643f47148c4235cc114bf15799d727acf1fec23c0eafbca7f752
---
# [fix] Add support for flashinfer MOE A2A to Qwen3 BF16 model path

URL: https://github.com/sgl-project/sglang/pull/26255
State: closed
Labels: quant, sgl-kernel, run-ci
Closed at: 2026-07-01T08:59:55Z
Merged at: 2026-07-01T08:59:55Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->
BF16 + DP attn + EP moe + flashinfer A2A + flashinfer MOE cutlass backend is currently not supported in sglang. This MR enables support for this and resolves some related issues that caused crashes


## Modifications

<!-- Detail the changes made in this pull request. -->

1. Handle non-existent `self.quant_config` in FlashinferDispatcher
2. Use communication buffer as moe output in `flashinfer_cutlass_fused_moe`
3. Skip duplicated allreduce (relevant for TP attn + EP moe)
4. Prevent top_k from silently raising an "invalid argument" error when DP tokens/rank = 0


## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
5. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
6. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
7. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.



























































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28414841085](https://github.com/sgl-project/sglang/actions/runs/28414841085)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28414841051](https://github.com/sgl-project/sglang/actions/runs/28414841051)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
