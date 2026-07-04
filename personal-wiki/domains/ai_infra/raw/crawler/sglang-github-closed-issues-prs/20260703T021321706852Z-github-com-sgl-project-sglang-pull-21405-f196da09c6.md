---
source_id: sglang-github-closed-issues-prs
title: Enable IndexCache for DeepSeek V3.2
canonical_url: https://github.com/sgl-project/sglang/pull/21405
captured_at: '2026-07-03T02:13:21.706852+00:00'
content_hash: f196da09c67a6baa8a501aa668cece19e3b339e18b55ea9db56d6499f8842661
---
# Enable IndexCache for DeepSeek V3.2

URL: https://github.com/sgl-project/sglang/pull/21405
State: closed
Labels: high priority, deepseek, run-ci
Closed at: 2026-04-05T09:45:58Z
Merged at: 2026-04-05T09:45:58Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

fix https://github.com/sgl-project/sglang/issues/21286

<!-- Describe the purpose and goals of this pull request. -->

## Modifications
* Port https://github.com/THUDM/IndexCache
* add ut for deepseek-v3.2
<!-- Detail the changes made in this pull request. -->

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->
```
python3 -m sglang.launch_server   --model-path /ssd/hf_models/DeepSeek-V3.2-Exp --tp 8 --mem-fraction-static=0.9 --tool-call-parser deepseekv32  --reasoning-parser deepseek-v3 --json-model-override-args '{"index_topk_freq": 4}'
```
```
lm_eval --model local-completions --model_args "base_url=http://127.0.0.1:30000/v1/completions,model=/ssd/hf_models/DeepSeek-V3.2-Exp,num_concurrent=100,tokenized_requests=False" --tasks gsm8k
```
gsm8k with DeepSeek-V3.2-Exp with this PR:
```
|Tasks|Version|     Filter     |n-shot|  Metric   |   |Value |   |Stderr|
|-----|------:|----------------|-----:|-----------|---|-----:|---|-----:|
|gsm8k|      3|flexible-extract|     5|exact_match|↑  |0.9583|±  |0.0055|
|     |       |strict-match    |     5|exact_match|↑  |0.9575|±  |0.0056|
```
main
```
|Tasks|Version|     Filter     |n-shot|  Metric   |   |Value |   |Stderr|
|-----|------:|----------------|-----:|-----------|---|-----:|---|-----:|
|gsm8k|      3|flexible-extract|     5|exact_match|↑  |0.9598|±  |0.0054|
|     |       |strict-match    |     5|exact_match|↑  |0.9575|±  |0.0056|
```
## Benchmarking and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

Throghput improved ~ +6.4%
TTFT improved ~ -5.4%
TPOT improved ~ -5.5%

```
python3 -m sglang.bench_serving   \
  --backend sglang \
  --host 127.0.0.1 \
  --port 30000 \
  --model /ssd/hf_models/DeepSeek-V3.2-Exp \
  --dataset-name random \
  --num-prompts 500 \
  --random-input-len 1024 \
  --random-output-len 512
```
this PR:
```
============ Serving Benchmark Result ============
Backend:                                 sglang
Traffic request rate:                    inf
Max request concurrency:                 not set
Successful requests:                     500
Benchmark duration (s):                  113.18
Total input tokens:                      253168
Total input text tokens:                 253168
Total generated tokens:                  131674
Total generated tokens (retokenized):    129011
Request throughput (req/s):              4.42
Input token throughput (tok/s):          2236.90
Output token throughput (tok/s):         1163.42
Peak output token throughput (tok/s):    1811.00
Peak concurrent requests:                500
Total token throughput (tok/s):          3400.32
Concurrency:                             267.13
----------------End-to-End Latency----------------
Mean E2E Latency (ms):                   60465.83
Median E2E Latency (ms):                 60908.48
P90 E2E Latency (ms):                    103027.63
P99 E2E Latency (ms):                    111428.53
---------------Time to First Token----------------
Mean TTFT (ms):                          47792.35
Median TTFT (ms):                        47176.86
P99 TTFT (ms):                           102048.78
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          49.13
Median TPOT (ms):                        49.81
P99 TPOT (ms):                           65.31
---------------Inter-Token Latency----------------
Mean ITL (ms):                           48.31
Median ITL (ms):                         35.71
P95 ITL (ms):                            116.53
P99 ITL (ms):                            158.38
Max ITL (ms):                            1811.18
==================================================
```
main
```
============ Serving Benchmark Result ============
Backend:                                 sglang
Traffic request rate:                    inf
Max request concurrency:                 not set
Successful requests:                     500
Benchmark duration (s):                  120.48
Total input tokens:                      253168
Total input text tokens:                 253168
Total generated tokens:                  131674
Total generated tokens (retokenized):    129011
Request throughput (req/s):              4.15
Input token throughput (tok/s):          2101.31
Output token throughput (tok/s):         1092.90
Peak output token throughput (tok/s):    1617.00
Peak concurrent requests:                500
Total token throughput (tok/s):          3194.21
Concurrency:                             265.43
----------------End-to-End Latency----------------
Mean E2E Latency (ms):                   63957.86
Median E2E Latency (ms):                 64404.77
P90 E2E Latency (ms):                    108928.34
P99 E2E Latency (ms):                    118216.62
---------------Time to First Token----------------
Mean TTFT (ms):                          50530.24
Median TTFT (ms):                        49860.22
P99 TTFT (ms):                           107822.09
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          52.01
Median TPOT (ms):                        52.70
P99 TPOT (ms):                           68.16
---------------Inter-Token Latency----------------
Mean ITL (ms):                           51.18
Median ITL (ms):                         38.67
P95 ITL (ms):                            121.57
P99 ITL (ms):                            160.03
Max ITL (ms):                            1821.74
==================================================
```

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review Process

1. Ping Merge Oncalls to start the PR flow. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - `/tag-run-ci-label`, `/rerun-failed-ci`, `/tag-and-rerun-ci`
4. After green CI and required approvals, ask Merge Oncalls to merge.
