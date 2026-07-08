---
source_id: sglang-github-closed-issues-prs
title: Adding prefill observability
canonical_url: https://github.com/sgl-project/sglang/pull/30316
captured_at: '2026-07-07T23:35:30.921872+00:00'
content_hash: 90a3db94eef0b62af6d9295abd070f4989680188674c897d5172e3afc3497d9a
---
# Adding prefill observability

URL: https://github.com/sgl-project/sglang/pull/30316
State: closed
Labels: dependencies, lora, Multi-modal, deepseek, hicache, blackwell, deterministic, model-gateway
Closed at: 2026-07-07T01:44:51Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

First pr of my intern project (https://app.notion.com/p/Cache-Aware-Image-Reuse-for-Next-Act-Inference-38e7c1d6cdc78029a32bd6d7193217a3) - implementing VLCache to cut multi turn TTFT when handling images. PR implements the measurement layer: server side prefill TTFT, plan vs forward split and ViT cache hit visibility. VLCache PR that follows can be benchmarked. Nothing here depends on VLCache.

## Modifications

Introduce general env vars to measure basic observability:
- SGLANG_PREFILL_FORWARD_TIMER=1: log GPU synced wall time per prefill forward. Off by 
- SGLANG_ATTN_PLAN_TIMER=1: log attention metadata planning time per prefill. Off by default.

mm_cache_stats: hit/miss counters for the multimodal (ViT) embedding cache. This is surfaced on prefill batch log line. 

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

no measurable overhead

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: **Missing `run-ci` label** -- add it to run CI tests.<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: **Blocked** -- `run-ci` is required first.<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
