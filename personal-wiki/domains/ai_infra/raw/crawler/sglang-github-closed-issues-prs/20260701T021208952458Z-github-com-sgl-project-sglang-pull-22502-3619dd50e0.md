---
source_id: sglang-github-closed-issues-prs
title: '[AMD][Qwen3.5] use a8w8 blockscale ck gemm for gfx942'
canonical_url: https://github.com/sgl-project/sglang/pull/22502
captured_at: '2026-07-01T02:12:08.952458+00:00'
content_hash: 3619dd50e0023aeffdab2befb4957c388d53dc11dc3ed6ab88e2a16df50cea38
---
# [AMD][Qwen3.5] use a8w8 blockscale ck gemm for gfx942

URL: https://github.com/sgl-project/sglang/pull/22502
State: closed
Labels: 
Closed at: 2026-07-01T01:31:03Z
Merged at: 

## Motivation

This PR enables CK fp8 gemm for fp8 models in gfx942 platform.

## Modifications

Use CK a8w8 blockscale gemm for fp8 gemm layers.

## Accuracy Tests

before this PR:
|Tasks|Version|     Filter     |n-shot|  Metric   |   |Value |   |Stderr|
|-----|------:|----------------|-----:|-----------|---|-----:|---|-----:|
|gsm8k|      3|flexible-extract|     5|exact_match|↑  |0.9629|±  |0.0052|
|     |       |strict-match    |     5|exact_match|↑  |0.9659|±  |0.0050|

after this PR:
|Tasks|Version|     Filter     |n-shot|  Metric   |   |Value |   |Stderr|
|-----|------:|----------------|-----:|-----------|---|-----:|---|-----:|
|gsm8k|      3|flexible-extract|     5|exact_match|↑  |0.9636|±  |0.0052|
|     |       |strict-match    |     5|exact_match|↑  |0.9666|±  |0.0049|

## Speed Tests and Profiling

before this PR:
| TP | CONC | ISL | OSL | Input TPUT per GPU | Output TPUT per GPU | Total TPUT per GPU|
|------|----------|------|------|----------|------|------|
| 8 | 4 | 1024 | 1024 | 24.03 | 22.29 | 46.32 |
| 8 | 4 | 1024 | 8192 | 3.21 | 23.01 | 26.22 |
| 8 | 4 | 8192 | 1024 | 134.49 | 16.59 | 151.08 |
| 8 | 8 | 1024 | 1024 | 41.5 | 38.34 | 79.84 |
| 8 | 8 | 1024 | 8192 | 5.34 | 39.75 | 45.09 |
| 8 | 8 | 8192 | 1024 | 254.53 | 30.87 | 285.4 |
| 8 | 16 | 1024 | 1024 | 62.83 | 61.91 | 124.75 |
| 8 | 16 | 1024 | 8192 | 8.55 | 70.49 | 79.04 |
| 8 | 16 | 8192 | 1024 | 413.79 | 52.08 | 465.87 |
| 8 | 32 | 1024 | 1024 | 94.29 | 99.48 | 193.77 |
| 8 | 32 | 1024 | 8192 | 14.43 | 120.71 | 135.14 |
| 8 | 32 | 8192 | 1024 | 655.95 | 85.50 | 741.45 |
| 8 | 64 | 1024 | 1024 | 138.21 | 135.35 | 273.55 |
| 8 | 64 | 1024 | 8192 | 22.87 | 177.37 | 200.24 |
| 8 | 64 | 8192 | 1024 | 903.88 | 110.52 | 1014.40 |

after this PR:

| TP | CONC | ISL | OSL | Input TPUT per GPU | Output TPUT per GPU | Total TPUT per GPU|
|------|----------|------|------|----------|------|------|
| 8 | 4 | 1024 | 1024 | 37.67| 34.93 | 72.60 |
| 8 | 4 | 1024 | 8192 | 5.17 | 37.05 | 42.22 |
| 8 | 4 | 8192 | 1024 | 267.98 | 33.06 | 301.03 |
| 8 | 8 | 1024 | 1024 | 62.65 | 57.89 | 120.53 |
| 8 | 8 | 1024 | 8192 | 8.26 | 61.52 | 69.79 |
| 8 | 8 | 8192 | 1024 | 441.23 | 53.52 | 494.75 |
| 8 | 16 | 1024 | 1024 | 98.87 | 97.42 | 196.30 |
| 8 | 16 | 1024 | 8192 | 13.67 | 112.65 | 126.31 |
| 8 | 16 | 8192 | 1024 | 699.12 | 87.99 | 787.10 |
| 8 | 32 | 1024 | 1024 | 139.57 | 147.25 | 286.82 |
| 8 | 32 | 1024 | 8192 | 21.56 | 180.33 | 201.89 |
| 8 | 32 | 8192 | 1024 | 977.01 | 127.34 | 1104.35 |
| 8 | 64 | 1024 | 1024 | 186.11 | 182.26 | 368.37 |
| 8 | 64 | 1024 | 8192 | 31.13 | 241.4 | 272.53 |
| 8 | 64 | 8192 | 1024 | 1232.7 | 150.73 | 1383.43 |

speedup: 1.3x~2.0x, average 1.56x

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
