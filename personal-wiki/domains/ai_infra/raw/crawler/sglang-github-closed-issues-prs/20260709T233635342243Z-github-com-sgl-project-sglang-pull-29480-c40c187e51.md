---
source_id: sglang-github-closed-issues-prs
title: '[NPU] Add extra topk_weights input in deepep ll dispatch'
canonical_url: https://github.com/sgl-project/sglang/pull/29480
captured_at: '2026-07-09T23:36:35.342243+00:00'
content_hash: c40c187e51b4d0629fb45b16f01fa136c0d0f1d9a17d95d6208b15b1a8965df1
---
# [NPU] Add extra topk_weights input in deepep ll dispatch

URL: https://github.com/sgl-project/sglang/pull/29480
State: closed
Labels: run-ci
Closed at: 2026-07-09T01:23:30Z
Merged at: 2026-07-09T01:23:30Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

To adapt to NPU ROCE networking, corresponding modifications have been implemented in DeepEP. The low_latency_dispatch structure now requires the topk_weights parameter to be passed. Therefore, the SGLang framework injects the topk_weights parameter in NPU scenarios to maintain compatibility with NPU deployments without ROCE networking.

## Modifications

python/sglang/srt/layers/moe/token_dispatcher/deepep.py

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28910951849](https://github.com/sgl-project/sglang/actions/runs/28910951849)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28910951759](https://github.com/sgl-project/sglang/actions/runs/28910951759)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
