---
source_id: sglang-github-closed-issues-prs
title: amd/deepseek_v4 integration 22/N enable SGLANG_OPT_DPSK_V4_RADIX=1 on ROCm
canonical_url: https://github.com/sgl-project/sglang/pull/25164
captured_at: '2026-07-11T23:37:37.775376+00:00'
content_hash: aeefd156061727f26f6614046d7773243eb5b89c8f3d48ff115a41270161103b
---
# amd/deepseek_v4 integration 22/N enable SGLANG_OPT_DPSK_V4_RADIX=1 on ROCm

URL: https://github.com/sgl-project/sglang/pull/25164
State: closed
Labels: deepseek
Closed at: 2026-05-14T07:57:10Z
Merged at: 2026-05-14T07:57:10Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

Update amd/deepseek_v4 integration branch

Following PRs have large set of conflict, we use this PR and upstream amd/deepseek_v4 branch to integrate in parallel.
https://github.com/sgl-project/sglang/pull/23600
https://github.com/sgl-project/sglang/pull/23608


## Motivation

Enable `SGLANG_OPT_DPSK_V4_RADIX=1` (paged SWA + prefix cache) on ROCm. The blocker was that V4 was previously routed through `PagedTokenToKVPoolAllocator`, which never populates `full_to_swa_index_mapping`; with radix=1 the SWA path needs that mapping. This PR routes V4 through the standard `SWATokenToKVPoolAllocator` so the mapping is built like any other SWA model.

Also requires `SGLANG_OPT_USE_OLD_COMPRESSOR=false` and removing `--disable-radix-cache` from the launch script.

## Modifications

<!-- Detail the changes made in this pull request. -->

- New `python/sglang/srt/mem_cache/base_swa_memory_pool.py`: `BaseSWAKVPool` ABC; both `SWAKVPool` and `DeepSeekV4TokenToKVPool` now implement it. The ABC only requires `swa_kv_pool` (not `full_kv_pool`) since V4 has no separate physical full pool.
- Modified `python/sglang/srt/mem_cache/swa_memory_pool.py`: `SWATokenToKVPoolAllocator` pulls `full_kv_pool` via `getattr(kvcache, "full_kv_pool", None)` so V4 plugs in cleanly.
- Modified `python/sglang/srt/mem_cache/deepseekv4_memory_pool.py`: `DeepSeekV4TokenToKVPool` inherits `BaseSWAKVPool` and adds a no-op `set_swa_loc` (V4 caches its own SWA loc internally).
- Modified `python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py`: drop the `is_v4_model` branch that previously routed V4 to `PagedTokenToKVPoolAllocator` and bypassed the SWA path.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

GSM8K 200-question 5-shot on DeepSeek-V4-Flash, 8x MI350X TP=8: **0.925 (radix=1) vs 0.930 (radix=0)** — within noise, zero invalid.

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

Prefix-share workload (`gsp 8x16`, 2K system prompt) on DeepSeek-V4-Flash, 8x MI350X TP=8: **TTFT P50 5355ms → 1682ms (-69%)**.

Decode-heavy workloads regress on TPOT (+56%); paged decode performance is a follow-up.

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
