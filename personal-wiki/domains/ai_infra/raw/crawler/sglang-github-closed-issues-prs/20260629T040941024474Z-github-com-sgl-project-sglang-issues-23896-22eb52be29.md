---
source_id: sglang-github-closed-issues-prs
title: '[Performance] DeepSeek-V4-Flash on H20-3e: Balanced (TP4+DP4+DeepEP) throughput
  lower than Low-Latency (TP4)'
canonical_url: https://github.com/sgl-project/sglang/issues/23896
captured_at: '2026-06-29T04:09:41.024474+00:00'
content_hash: 22eb52be29fd86702970dee845f3d2fb5410385a2a47c76e15c4030fbdfe9bf6
---
# [Performance] DeepSeek-V4-Flash on H20-3e: Balanced (TP4+DP4+DeepEP) throughput lower than Low-Latency (TP4)

URL: https://github.com/sgl-project/sglang/issues/23896
State: closed
Labels: inactive
Closed at: 2026-06-29T00:51:16Z
Merged at: 

## Environment

- **GPU**: 4 × NVIDIA H20-3e
- **Model**: DeepSeek-V4-Flash-FP8 (`sgl-project/DeepSeek-V4-Flash-FP8`)
- **SGLang image**: `lmsysorg/sglang:deepseek-v4-hopper`

## Configurations

### Config A — Balanced recipe (TP4 + DP4 + DeepEP)

```yaml
environment:
  - CUDA_VISIBLE_DEVICES=4,5,6,7
  - SGLANG_ENABLE_SPEC_V2=1
  - SGLANG_DSV4_FP4_EXPERTS=0
  - SGLANG_JIT_DEEPGEMM_PRECOMPILE=0
  - SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=256
command:
  sglang serve
    --trust-remote-code
    --model-path /root/.cache/huggingface/DeepSeek-V4-Flash-FP8
    --tp 4 
    --dp 4 
    --enable-dp-attention
    --moe-a2a-backend deepep
    --deepep-config '{"normal_dispatch":{"num_sms":48},"normal_combine":{"num_sms":48}}'
    --mem-fraction-static 0.8
    --cuda-graph-max-bs 128
    --max-running-requests 128
    --speculative-algo EAGLE
    --speculative-num-steps 1
    --speculative-eagle-topk 1
    --speculative-num-draft-tokens 2
    --host 0.0.0.0 --port 8000
```

### Config B — Low-Latency recipe (Pure TP4)

```yaml
environment:
  - CUDA_VISIBLE_DEVICES=4,5,6,7
  - SGLANG_ENABLE_SPEC_V2=1
  - SGLANG_DSV4_FP4_EXPERTS=0
  - SGLANG_JIT_DEEPGEMM_PRECOMPILE=0
command:
  sglang serve
    --trust-remote-code
    --model-path /root/.cache/huggingface/DeepSeek-V4-Flash-FP8
    --tp 4
    --mem-fraction-static 0.8
    --cuda-graph-max-bs 128
    --max-running-requests 128
    --speculative-algo EAGLE 
    --speculative-num-steps 3 
    --speculative-eagle-topk 1
    --speculative-num-draft-tokens 4
    --host 0.0.0.0 --port 8000
```

## Benchmark

- Tool: `python3 -m sglang.bench_serving`
- Params: `--random-input-len 1024 --random-output-len 1024 --num-prompts 1000 --max-concurrency 100`
- Identical workload across both runs: 512,842 input tokens, 510,855 output tokens

### Config B (TP4 Low-Latency) raw output

```
============ Serving Benchmark Result ============
Backend:                                 sglang
Traffic request rate:                    inf
Max request concurrency:                 100
Successful requests:                     1000
Benchmark duration (s):                  418.03
Total input tokens:                      512842
Total input text tokens:                 512842
Total generated tokens:                  510855
Total generated tokens (retokenized):    510773
Request throughput (req/s):              2.39
Input token throughput (tok/s):          1226.81
Output token throughput (tok/s):         1222.06
Peak output token throughput (tok/s):    3713.00
Peak concurrent requests:                110
Total token throughput (tok/s):          2448.87
Concurrency:                             97.41
Accept length:                           2.86
----------------End-to-End Latency----------------
Mean E2E Latency (ms):                   40720.71
Median E2E Latency (ms):                 28510.99
P90 E2E Latency (ms):                    87745.65
P99 E2E Latency (ms):                    192868.19
---------------Time to First Token----------------
Mean TTFT (ms):                          5321.56
Median TTFT (ms):                        322.01
P99 TTFT (ms):                           56565.52
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          79.29
Median TPOT (ms):                        53.27
P99 TPOT (ms):                           633.75
---------------Inter-Token Latency----------------
Mean ITL (ms):                           69.42
Median ITL (ms):                         33.33
P95 ITL (ms):                            115.28
P99 ITL (ms):                            718.89
Max ITL (ms):                            22832.40
==================================================
```

### Config A (TP4+DP4+DeepEP Balanced) raw output

```
============ Serving Benchmark Result ============
Backend:                                 sglang
Traffic request rate:                    inf
Max request concurrency:                 100
Successful requests:                     1000
Benchmark duration (s):                  408.70
Total input tokens:                      512842
Total input text tokens:                 512842
Total generated tokens:                  510855
Total generated tokens (retokenized):    510761
Request throughput (req/s):              2.45
Input token throughput (tok/s):          1254.81
Output token throughput (tok/s):         1249.95
Peak output token throughput (tok/s):    3727.00
Peak concurrent requests:                110
Total token throughput (tok/s):          2504.75
Concurrency:                             96.77
Accept length:                           1.97
----------------End-to-End Latency----------------
Mean E2E Latency (ms):                   39549.45
Median E2E Latency (ms):                 28794.77
P90 E2E Latency (ms):                    78183.29
P99 E2E Latency (ms):                    179027.32
---------------Time to First Token----------------
Mean TTFT (ms):                          6386.98
Median TTFT (ms):                        334.98
P99 TTFT (ms):                           93489.00
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          80.39
Median TPOT (ms):                        53.49
P99 TPOT (ms):                           593.43
---------------Inter-Token Latency----------------
Mean ITL (ms):                           65.04
Median ITL (ms):                         27.36
P95 ITL (ms):                            125.44
P99 ITL (ms):                            356.68
Max ITL (ms):                            52277.16
==================================================
```

### Comparison

| Metric | A: Balanced (TP4+DP4+DeepEP) | B: Low-Latency (TP4) |
|---|---|---|
| Duration (s) | 408.70 | **393.80** |
| Output throughput (tok/s) | 1249.95 | **1297.25** |
| Request throughput (req/s) | 2.45 | **2.54** |
| Mean TTFT (ms) | 6386.98 | **5769.77** |
| Mean TPOT (ms) | 80.39 | **75.18** |
| Mean ITL (ms) | 65.04 | **63.31** |

The Balanced recipe underperforms Low-Latency on every metric by approximately 3–6%.

## Analysis and Questions

### 1. DeepEP num_sms and H20 compute limitation

The H20 has only 78 SMs. The H200 recipe uses `num_sms=96` . We tried:

- `num_sms=78` — worse than pure TP
- `num_sms=48` — slightly better than `num_sms=78` but still behind pure TP

Our hypothesis is that the H20 has significantly lower compute capacity than the H200, making compute the bottleneck. DeepEP's communication-computation overlap cannot compensate when SMs are already saturated by GEMM. For low-compute GPUs like the H20, is the Balanced/DP recipe inherently unsuitable?

### 2. Reference data on real H200

On actual H200 hardware, how much throughput improvement does the Balanced recipe typically show over Low-Latency for DeepSeek-V4-Flash? The cookbook doesn't yet include benchmark data — are there internal numbers the community could reference?

### 3. Further tuning directions

Are there other knobs we should try to validate our hypothesis or improve DP throughput on H20? For example:

- Increasing `max-running-requests` ?
- Adjusting `SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK` ?
- Disabling MTP speculation entirely ?
- Further reducing `num_sms` for DeepEP ?
