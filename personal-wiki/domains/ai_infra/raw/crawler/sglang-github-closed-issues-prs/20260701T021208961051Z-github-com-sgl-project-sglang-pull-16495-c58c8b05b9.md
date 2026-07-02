---
source_id: sglang-github-closed-issues-prs
title: '[hicache-ci] Add accuracy evaluation support for caches loaded from memory'
canonical_url: https://github.com/sgl-project/sglang/pull/16495
captured_at: '2026-07-01T02:12:08.961051+00:00'
content_hash: c58c8b05b97c3e3e46837d04b74f70d06e61783e56968b42f34a91e8922d1c9d
---
# [hicache-ci] Add accuracy evaluation support for caches loaded from memory

URL: https://github.com/sgl-project/sglang/pull/16495
State: closed
Labels: hicache, run-ci
Closed at: 2026-06-30T07:59:09Z
Merged at: 

Hi from [novita.ai](https://novita.ai/) team 👋
<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation
Add accuracy evaluation support for caches loaded from memory
<!-- Describe the purpose and goals of this pull request. -->

## Modifications

<!-- Detail the changes made in this pull request. -->

## Accuracy Tests
load from device
```
Total latency: 25.713 s
Score: 0.734
```
load from memory
```
Total latency: 25.487 s
Score: 0.750
```
diff 
```
Accuracy difference: 0.0156
```
test passed
```
2 passed, 2 warnings in 136.93s (0:02:16)
```
<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Benchmarking and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review Process

1. Ping Merge Oncalls to start the PR flow. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) (`/tag-run-ci-label`, `/rerun-failed-ci`, `/tag-and-rerun-ci`) or contact authorized users to do so.
4. After green CI and required approvals, ask Merge Oncalls to merge.
