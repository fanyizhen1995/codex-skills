---
source_id: sglang-github-closed-issues-prs
title: Fix scheduler crash on prefill-unreachable decode abort
canonical_url: https://github.com/sgl-project/sglang/pull/29834
captured_at: '2026-07-08T23:36:33.797422+00:00'
content_hash: c59e7a335d449cf1befae1d0b84f968391daf9e7939c684a4556cc7a68f3c4bd
---
# Fix scheduler crash on prefill-unreachable decode abort

URL: https://github.com/sgl-project/sglang/pull/29834
State: closed
Labels: run-ci
Closed at: 2026-07-08T06:06:38Z
Merged at: 2026-07-08T06:06:38Z

When the prefill bootstrap server is unreachable, a DecodeRequest shared between self.queue and self.pending_reqs (add() slow path) has its kv_receiver set to None by the abort path (PR #28022), but only self.queue is cleaned up. The dangling pending_reqs reference then crashes the next _resolve_pending_reqs:

  AttributeError: 'NoneType' object has no attribute 'abort'

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

Fix scheduler crash on prefill-unreachable decode abort

## Modifications

<!-- Detail the changes made in this pull request. -->

- Drop failed reqs from pending_reqs after the abort loop (identity via id(), since DecodeRequest's dataclass __eq__ compares the tensor receiver).
- Guard .abort() against a None receiver as a backstop.
- Add two regression tests (the existing suite set pending_reqs=[], which masked this case).

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

N/A

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

N/A

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
3. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
4. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
5. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.



























































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28800644979](https://github.com/sgl-project/sglang/actions/runs/28800644979)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28800644923](https://github.com/sgl-project/sglang/actions/runs/28800644923)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
