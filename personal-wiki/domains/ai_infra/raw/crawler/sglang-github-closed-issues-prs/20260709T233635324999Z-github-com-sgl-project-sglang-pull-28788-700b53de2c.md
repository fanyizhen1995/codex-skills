---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Fix int32 offset overflow in Triton decode-attention kernels'
canonical_url: https://github.com/sgl-project/sglang/pull/28788
captured_at: '2026-07-09T23:36:35.324999+00:00'
content_hash: 700b53de2cdcc94edf51aa5b6393b2866bdf1d0b6427be21dac61b593fc55192
---
# [AMD] Fix int32 offset overflow in Triton decode-attention kernels

URL: https://github.com/sgl-project/sglang/pull/28788
State: closed
Labels: run-ci, bypass-fastfail, run-ci-extra
Closed at: 2026-07-09T18:20:04Z
Merged at: 2026-07-09T18:20:04Z

The decode-attention stage1/stage1-grouped/stage2 kernels index the flat `Mid_O`/`Mid_O_1` scratch buffers using `cur_batch * stride`, where `cur_batch = tl.program_id(0)` is int32. When `max_kv_splits` is large (e.g. ceil(context_len/256) ~ 792 for long-context MLA models) and CUDA graph captures large batch sizes, so `batch * num_head * max_kv_splits * head_dim` can exceed 2**31. The int32 offset then overflows and the kernel reads/writes out of bounds, crashing CUDA graph capture with "Memory access fault by GPU".

Widen the program id to int64 at each kernel entry so offset arithmetic is computed in int64.

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

## Modifications

<!-- Detail the changes made in this pull request. -->

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28912840015](https://github.com/sgl-project/sglang/actions/runs/28912840015)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28912839842](https://github.com/sgl-project/sglang/actions/runs/28912839842)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
