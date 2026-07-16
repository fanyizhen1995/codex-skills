---
source_id: sglang-github-closed-issues-prs
title: 'fix: fix mamba memory leak'
canonical_url: https://github.com/sgl-project/sglang/pull/20182
captured_at: '2026-07-13T23:40:05.193382+00:00'
content_hash: bce4b4299416beea094abbe5738bd961f18b00a981240136a86865a5b12cbede
---
# fix: fix mamba memory leak

URL: https://github.com/sgl-project/sglang/pull/20182
State: closed
Labels: run-ci
Closed at: 2026-07-13T02:57:18Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

#20010
#20069 

This PR fixes a memory leak that can crash the scheduler with: 
`ValueError: token_to_kv_pool_allocator memory leak detected!`

**Root Cause:** For models using DeltaNet/Mamba, `match_prefix` may allocate `req.mamba_pool_idx` before the request fully enters the running state. If that request is later aborted while it's still in the waiting queue (e.g. queue full, timeout), the pre-allocated mamba state is unreleased, and the idle memory checker then reports leaked pages

## Modifications

Added a cleanup helper `_cleanup_waiting_request_resources(req)` that is now applied to `_abort_on_queued_limit`, `_abort_on_waiting_timeout`, and `abort_request`.

A test is added that triggers the memory leak bug by manually creating crowded condition that could trigger both  `_abort_on_queued_limit` and `_abort_on_waiting_timeout`. It now passes after the change.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Benchmarking and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review Process

1. Ping Merge Oncalls to start the PR flow. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - `/tag-run-ci-label`, `/rerun-failed-ci`, `/tag-and-rerun-ci`
4. After green CI and required approvals, ask Merge Oncalls to merge.
