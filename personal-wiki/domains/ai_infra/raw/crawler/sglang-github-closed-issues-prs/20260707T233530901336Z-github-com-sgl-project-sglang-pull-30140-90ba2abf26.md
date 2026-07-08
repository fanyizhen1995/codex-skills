---
source_id: sglang-github-closed-issues-prs
title: '[DeepSeek-V4] Enable non-paged indexer by default for large prefill chunks'
canonical_url: https://github.com/sgl-project/sglang/pull/30140
captured_at: '2026-07-07T23:35:30.901336+00:00'
content_hash: 90ba2abf26300d41f2ff76acdf8df3b1d91003ca40db158f1036bd59f763a491
---
# [DeepSeek-V4] Enable non-paged indexer by default for large prefill chunks

URL: https://github.com/sgl-project/sglang/pull/30140
State: closed
Labels: 
Closed at: 2026-07-07T22:51:25Z
Merged at: 2026-07-07T22:51:25Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

The non-paged DeepSeek-V4 indexer improves large local prefill queries, while its fixed gather cost can regress small queries. Enable it by default only in the measured safe region.

## Modifications

- Enable the non-paged indexer by default.
- Keep local queries below 8,192 rows on the paged path and preserve the explicit opt-out and existing fail-closed guards.
- Add default, boundary, fallback, and fast-path unit coverage.

## Accuracy Tests

This follow-up only changes the default path selection; it does not change kernel math. The non-paged path was accuracy-tested as part of [#29619](https://github.com/sgl-project/sglang/pull/29619).

| Evaluation | Result |
|---|---|
| GSM8K | 96.59% (1,274 / 1,319); 0 errors, 0 truncated |
| AIME25 clean rerun (16 repeats) | pass@1 99.58% (478 / 480); pass@16 100%; majority@16 100%; 0 errors, 0 truncated |

Paged/non-paged logits and top-k parity remained bit-exact on H100 and GB300 (`rtol=0`, `atol=0`). Current-head B200 unit tests passed: `5 passed`, `12 subtests passed`.

## Speed Tests and Profiling

### End-to-end serving

Real-serving tests used OSL=1 and an effective local prefill chunk of 8,192 tokens/rank. Global concurrency was 64 for 8K–64K and 16 for 128K. Each row is a four-arm `OFF → default → default → OFF` comparison with a 600-second measurement window per arm. Pair gain compares adjacent default/control runs; ABBA gain is their position-balanced geometric mean. The server windows were fully saturated with no cache reuse or fatal errors.

| Nominal ISL | Concurrency | A1 OFF TPS/rank | B1 default TPS/rank | Pair 1 | B2 default TPS/rank | A2 OFF TPS/rank | Pair 2 | ABBA gain |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 8K | 64 | 14,853.364 | 14,864.640 | +0.076% | 14,866.710 | 14,741.240 | +0.851% | +0.463% |
| 16K | 64 | 14,500.505 | 14,572.557 | +0.497% | 14,570.733 | 14,549.204 | +0.148% | +0.322% |
| 32K | 64 | 14,288.744 | 14,365.048 | +0.534% | 14,379.434 | 14,201.313 | +1.254% | **+0.894%** |
| 64K | 64 | 13,656.240 | 13,898.912 | +1.777% | 13,903.302 | 13,728.748 | +1.271% | **+1.524%** |
| 128K | 16 | 12,477.434 | 12,976.438 | +3.999% | 13,025.532 | 12,526.157 | +3.987% | **+3.993%** |

Both serial pairs were positive at every ISL. The effect is small at 8K–16K and increases at longer contexts as the gather cost is amortized over more prefix work.

### Benchmark

The table below is a kernel-level benchmark used to choose the default-path boundary. It compares paged MQA with gather + non-paged MQA on B200. `Local Q` is the number of query tokens handled by one rank in the current prefill forward, not the request ISL. `C4 prefix rows` is the compressed K length already present before that query block; one C4 row represents four raw tokens. Run 1 and Run 2 repeat the same comparison in different execution orders. Gain is `(paged - gather_and_nonpaged) / paged`, so a positive value means non-paged is faster.

| Local Q | C4 prefix rows | Run 1 gain | Run 2 gain | Default path |
|---:|---:|---:|---:|---|
| 1,024 | 0 | -235.358% | -243.614% | Paged |
| 1,024 | 2,048 | -104.526% | -113.013% | Paged |
| 1,024 | 8,192 | -38.539% | -43.769% | Paged |
| 1,024 | 32,768 | +5.742% | +2.691% | Paged |
| 1,024 | 65,536 | +8.801% | +8.930% | Paged |
| 1,024 | 125,000 | +9.836% | +12.322% | Paged |
| 2,048 | 0 | -152.328% | -163.805% | Paged |
| 2,048 | 2,048 | -56.194% | -61.544% | Paged |
| 2,048 | 8,192 | +2.338% | +1.016% | Paged |
| 2,048 | 32,768 | +19.811% | +19.533% | Paged |
| 2,048 | 65,536 | +22.350% | +22.966% | Paged |
| 2,048 | 125,000 | +26.031% | +29.633% | Paged |
| 4,096 | 0 | -54.036% | -56.494% | Paged |
| 4,096 | 2,048 | -13.225% | -22.011% | Paged |
| 4,096 | 8,192 | +17.633% | +15.409% | Paged |
| 4,096 | 32,768 | +23.480% | +23.361% | Paged |
| 4,096 | 65,536 | +28.609% | +29.648% | Paged |
| 4,096 | 125,000 | +33.240% | +33.782% | Paged |
| 6,144 | 0 | -10.209% | +0.617% | Paged |
| 6,144 | 2,048 | +5.285% | +4.427% | Paged |
| 6,144 | 8,192 | +19.414% | +18.322% | Paged |
| 6,144 | 32,768 | +27.707% | +26.005% | Paged |
| 6,144 | 65,536 | +33.260% | +33.393% | Paged |
| 6,144 | 125,000 | +35.173% | +34.880% | Paged |
| 7,168 | 0 | +24.653% | +13.163% | Paged |
| 7,168 | 2,048 | +7.977% | +6.099% | Paged |
| 7,168 | 8,192 | +19.890% | +18.672% | Paged |
| 7,168 | 32,768 | +25.049% | +27.483% | Paged |
| 7,168 | 65,536 | +32.952% | +32.908% | Paged |
| 7,168 | 125,000 | +34.796% | +34.590% | Paged |
| 8,192 | 0 | +35.139% | +33.015% | Non-paged |
| 8,192 | 2,048 | +17.475% | +16.672% | Non-paged |
| 8,192 | 8,192 | +22.810% | +21.668% | Non-paged |
| 8,192 | 32,768 | +30.323% | +30.513% | Non-paged |
| 8,192 | 65,536 | +33.333% | +33.151% | Non-paged |
| 8,192 | 125,000 | +35.477% | +35.197% | Non-paged |
| 10,240 | 0 | +45.810% | +44.737% | Non-paged |
| 10,240 | 2,048 | +18.119% | +17.105% | Non-paged |
| 10,240 | 8,192 | +24.110% | +23.570% | Non-paged |
| 10,240 | 32,768 | +30.377% | +33.116% | Non-paged |
| 10,240 | 65,536 | +34.282% | +34.812% | Non-paged |
| 10,240 | 125,000 | +35.350% | +35.074% | Non-paged |
| 12,288 | 0 | +52.223% | +51.412% | Non-paged |
| 12,288 | 2,048 | +21.732% | +22.914% | Non-paged |
| 12,288 | 8,192 | +23.864% | +22.288% | Non-paged |
| 12,288 | 32,768 | +33.491% | +33.961% | Non-paged |
| 12,288 | 65,536 | +34.463% | +34.974% | Non-paged |
| 12,288 | 125,000 | +34.867% | +35.248% | Non-paged |
| 16,384 | 0 | +58.611% | +57.645% | Non-paged |
| 16,384 | 2,048 | +28.359% | +27.780% | Non-paged |
| 16,384 | 8,192 | +26.891% | +26.087% | Non-paged |
| 16,384 | 32,768 | +34.115% | +34.278% | Non-paged |
| 16,384 | 65,536 | +35.369% | +35.317% | Non-paged |
| 16,384 | 125,000 | +35.044% | +34.754% | Non-paged |
| 32,768 | 0 | +57.037% | +56.715% | Non-paged |
| 32,768 | 32,768 | +35.172% | +34.703% | Non-paged |
| 32,768 | 125,000 | +35.168% | +35.040% | Non-paged |

Non-paged generally becomes more favorable as `Local Q` and the C4 prefix grow because the gather is amortized over more Q-by-K work. The trend is not strictly monotonic at every shape, but the safe boundary is clear: every tested `Q >= 8192` case improved in both runs, while smaller Q can regress, especially with short prefixes.

The same boundary holds across architectures: at `Q=6144`, H100 and GB300 regressed by `8.78%` and `49.33%`; at `Q=8192`, they improved by `8.82%` and `6.26%`. Therefore, this change conservatively selects non-paged at `Local Q >= 8192` and keeps paged below it. A real-serving GB300 profile at `Q=8192` also reduced the replaced p50 GPU span from `1.524 ms` to `1.068 ms`, including gather.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28722513145](https://github.com/sgl-project/sglang/actions/runs/28722513145)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28901105817](https://github.com/sgl-project/sglang/actions/runs/28901105817)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
