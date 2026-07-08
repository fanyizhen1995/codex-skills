---
source_id: sglang-github-closed-issues-prs
title: '[BugFix] Release HiCache prefetch resources on disagg-prefill bootstrap-queue
  abort'
canonical_url: https://github.com/sgl-project/sglang/pull/30053
captured_at: '2026-07-06T02:14:53.060525+00:00'
content_hash: c86bbf35fbd5ed717c705a1338ab6d7afc23aa1927d66dba3c82b38407236af9
---
# [BugFix] Release HiCache prefetch resources on disagg-prefill bootstrap-queue abort

URL: https://github.com/sgl-project/sglang/pull/30053
State: closed
Labels: hicache, run-ci, bypass-fastfail, run-ci-extra
Closed at: 2026-07-05T16:07:00Z
Merged at: 2026-07-05T16:07:00Z



## Motivation

When `abort_request()` processes requests still in `disagg_prefill_bootstrap_queue`, it aborts the KV sender but never calls `release_aborted_request()`. Since `_add_request_to_queue()` calls `_prefetch_kvcache()` (which increments `prefetch_tokens_occupied` and creates an `ongoing_prefetch` entry) before adding the request to the bootstrap queue, each aborted bootstrap-queue request permanently leaks `len(prefetch_key)` tokens from the counter. Once the counter exceeds `prefetch_capacity_limit`, `prefetch_rate_limited()` returns `True` for every subsequent request and storage prefetch is permanently disabled for the lifetime of the process.

The waiting-queue abort path already calls `release_aborted_request()` (line 3857); the bootstrap-queue path was never updated to match.

Introduced in v0.5.12 by #23631 (commit 233048212a).

Relates to #26886, #27619.

## Modifications

Call `release_aborted_request()` in the bootstrap-queue abort loop, gated on `self.enable_hicache_storage`, matching the waiting-queue pattern.

## Checklist

- [x] Format: `pre-commit run --all-files`
- [x] The fix is a 3-line addition following the existing pattern

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28727371683](https://github.com/sgl-project/sglang/actions/runs/28727371683)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28727371619](https://github.com/sgl-project/sglang/actions/runs/28727371619)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
