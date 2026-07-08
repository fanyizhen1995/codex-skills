---
source_id: sglang-github-closed-issues-prs
title: '[Unified Radix Cache] Rename tree variables to cache in unittest'
canonical_url: https://github.com/sgl-project/sglang/pull/30281
captured_at: '2026-07-07T23:35:30.915010+00:00'
content_hash: 4f073eeeba8c32ae23859c2694631dd6402b49c73aa3c93ab4ab1eb6381fb74d
---
# [Unified Radix Cache] Rename tree variables to cache in unittest

URL: https://github.com/sgl-project/sglang/pull/30281
State: closed
Labels: run-ci
Closed at: 2026-07-07T03:48:38Z
Merged at: 2026-07-07T03:48:38Z

## Motivation

- Pure variable rename
- Preparation change for #29901 for TreeCore split (UnifiedRadixCache would be "cache", while TreeCore  would be "cache.tree_core".

## Modifications

s/tree./cache. in unified radix cache unit tests.

## Accuracy Tests

N/A only unit tests are updated.

## Speed Tests and Profiling

N/A only unit tests are updated.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28811371151](https://github.com/sgl-project/sglang/actions/runs/28811371151)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28811370451](https://github.com/sgl-project/sglang/actions/runs/28811370451)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
