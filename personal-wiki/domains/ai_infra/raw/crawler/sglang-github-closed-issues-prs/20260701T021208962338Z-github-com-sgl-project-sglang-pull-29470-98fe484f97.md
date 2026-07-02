---
source_id: sglang-github-closed-issues-prs
title: '[GLM-5] Tune the threshold of router GEMM'
canonical_url: https://github.com/sgl-project/sglang/pull/29470
captured_at: '2026-07-01T02:12:08.962338+00:00'
content_hash: 98fe484f976ec261f826e391b9f36feb809059fed102115c1d9b44e4132409ad
---
# [GLM-5] Tune the threshold of router GEMM

URL: https://github.com/sgl-project/sglang/pull/29470
State: closed
Labels: deepseek, run-ci
Closed at: 2026-06-29T21:19:25Z
Merged at: 2026-06-29T21:19:25Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

It seem that it will be very difficult for microbenchmarks to the amount of PDL overlap with the next kernel (and thus E2E performance timing), even with cold L2 + CUPTI + CUDA graph, or warm L2 + CUDA graph. When Torch is using splitK mode for very small problem size. Caused by https://github.com/sgl-project/sglang/pull/21531/changes

After doing a little research https://github.com/vllm-project/vllm/pull/44217 (which uses warm L2 and is not entirely correct, but the point is similar) and https://github.com/lightseekorg/tokenspeed/pull/33 (for E = 384)

So, use a crossover testing of 1K/1K, token sweep from 1 to 16, to find the real threshold.

Performance result on SM103:

### GLM-5.2 1K-1K

With router GEMM vs without [M, 6144] x [256, 6144]:

| Concurrency | Median ITL (ms) WITH | Median ITL (ms) WITHOUT | Output Throughput (tok/s) WITH | Output Throughput (tok/s) WITHOUT | Winner |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 7.988 | 8.090 | 123.84 | 122.18 | WITH (+1.4%) |
| 2 | 8.464 | 8.627 | 233.69 | 228.84 | WITH (+2.1%) |
| 3 | 9.471 | 9.556 | 311.61 | 308.29 | WITH (+1.1%) |
| 4 | 9.447 | 9.530 | 416.25 | 412.18 | WITH (+1.0%) |
| 5 | 10.703 | 10.509 | 459.92 | 468.19 | WITHOUT (+1.8%) |
| 8 | 11.214 | 11.015 | 698.87 | 710.61 | WITHOUT (+1.7%) |
| 12 | 12.525 | 12.317 | 934.72 | 950.18 | WITHOUT (+1.7%) |
| 16 | 13.835 | 13.358 | 1123.77 | 1162.44 | WITHOUT (+3.4%) |

<img width="1469" height="741" alt="Screenshot 2026-06-26 at 6 14 05 PM" src="https://github.com/user-attachments/assets/23d2bc5b-e3ef-4f0b-a15d-5a72a6575f68" />

For example, for num tokens = 8, it will (essentially) fail to PDL overlap. Also PyTorch has improved this problem size on SM10X too. (Remember, this kernel was introduced in May 2025)

Vs. using PyTorch GEMM:
<img width="1462" height="788" alt="Screenshot 2026-06-26 at 6 13 50 PM" src="https://github.com/user-attachments/assets/d1ee6fb4-580c-4143-81d3-7dff8532552c" />

<!-- Describe the purpose and goals of this pull request. -->

## Modifications

Change it. Need more careful testing in the future for these sort of changes.

| Concurrency | Median ITL (ms) FIXED | Median ITL (ms) WITHOUT | Output Throughput (tok/s) FIXED | Output Throughput (tok/s) WITHOUT | Winner |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 7.996 | 8.090 | 123.72 | 122.18 | FIXED (+1.3%) |
| 2 | 8.487 | 8.627 | 232.98 | 228.84 | FIXED (+1.8%) |
| 3 | 9.457 | 9.556 | 312.48 | 308.29 | FIXED (+1.4%) |
| 4 | 9.435 | 9.530 | 417.32 | 412.18 | FIXED (+1.2%) |
| 5 | 10.510 | 10.509 | 468.36 | 468.19 | Tie |
| 8 | 11.017 | 11.015 | 711.05 | 710.61 | Tie |
| 12 | 12.308 | 12.317 | 950.27 | 950.18 | Tie |
| 16 | 13.355 | 13.358 | 1162.81 | 1162.44 | Tie |

<!-- Detail the changes made in this pull request. -->

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->



































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28325522191](https://github.com/sgl-project/sglang/actions/runs/28325522191)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28325522125](https://github.com/sgl-project/sglang/actions/runs/28325522125)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
