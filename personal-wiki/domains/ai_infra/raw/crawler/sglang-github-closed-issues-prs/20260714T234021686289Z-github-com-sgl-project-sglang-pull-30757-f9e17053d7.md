---
source_id: sglang-github-closed-issues-prs
title: '[PD] Fix HiSparse + SWA decode hang/rejection for long inputs'
canonical_url: https://github.com/sgl-project/sglang/pull/30757
captured_at: '2026-07-14T23:40:21.686289+00:00'
content_hash: f9e17053d7f781148933bf4d93b95ab71de7dd87f6bc603f0d279082cdcdbd7d
---
# [PD] Fix HiSparse + SWA decode hang/rejection for long inputs

URL: https://github.com/sgl-project/sglang/pull/30757
State: closed
Labels: 
Closed at: 2026-07-14T02:04:50Z
Merged at: 

On a decode node running DeepSeek-V4 (hybrid SWA) with HiSparse under PD disaggregation, long-input requests are wrongly rejected (HTTP 400) or stall in KV transfer until the bootstrap timeout fires. Disabling HiSparse with an otherwise identical config makes the same requests pass.

Root cause: the HiSparse decode pre-alloc path collapses the single-request limit to the SWA pool (~full/10) in two independent places, because the `DeepSeekV4HiSparseTokenToKVPoolAllocator` wrapper does not expose the underlying SWA allocator's tail-window semantics.

  1. Admission control used `logical_attn_allocator.available_size()` (= min(full, swa)), so a request whose input+output exceeds the SWA pool can never be admitted, or an in-flight long request starves the SWA-bounded budget of everything behind it. The full-attention pool is the real binding constraint for the whole request length; SWA is separately gated by the swa_tail check. Use `full_available_size()`.

  2. Pre-alloc used `alloc_logical_only`, which reserves SWA at the full prompt length. A single long request nearly fills the SWA pool, leaving too few spare pages for decode to make progress before eviction catches up. When `_uses_swa_tail_prealloc()` holds, allocate the sliding-window tail only via `alloc_extend_swa_tail` and set `req.swa_evicted_seqlen`, matching the non-HiSparse path.

Also forward `alloc_extend_swa_tail` on the HiSparse allocator so `_uses_swa_tail_prealloc()` resolves to True; the wrapper only changes the c4 (device) pool, not SWA, so delegating to the wrapped SWA allocator is safe.

Fixes #30401

cc @alphabetc1 @yhyang201

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

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29076368059](https://github.com/sgl-project/sglang/actions/runs/29076368059)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29076367839](https://github.com/sgl-project/sglang/actions/runs/29076367839)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
