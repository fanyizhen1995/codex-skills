---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Implement QuarkW4A8MXFp4MoE to support amd/gpt-oss-120b-w-mxfp4-a-fp8'
canonical_url: https://github.com/sgl-project/sglang/pull/27204
captured_at: '2026-07-01T02:12:08.959636+00:00'
content_hash: caabbbf53962f503bb76924291250f772d68b0c1a5aec8a0ccfa0fd2baa990e0
---
# [AMD] Implement QuarkW4A8MXFp4MoE to support amd/gpt-oss-120b-w-mxfp4-a-fp8

URL: https://github.com/sgl-project/sglang/pull/27204
State: closed
Labels: amd, run-ci
Closed at: 2026-06-30T08:24:23Z
Merged at: 2026-06-30T08:24:23Z

  This PR extends the Quark quantization scheme to support W4A8 MXFP4-FP8 path so SGLang can load and run AMD Quark per-expert MoE checkpoints through the AITER fused-MoE backend. The main motivation is enabling support for amd/gpt-oss-120b-w-mxfp4-a-fp8 (checkpoint carries fp8 scaling for activation - pre-calib).

  The change mirrors the existing native MXFP4 GPT-OSS loading flow where possible, while handling the Quark checkpoint layout differences explicitly. It also tightens backend auto-detection on ROCm so these checkpoints use the expected AITER path and separated gate/up layout.

  Main changes:

  - Add GPT-OSS Quark per-expert MoE weight loading for gate_up_proj and down_proj weights, scales, input scales,
    and biases.
  - Align Quark W4A8 MXFP4-FP8 MoE execution with the existing GPT-OSS AITER MXFP4 path, including padding, bias
    plumbing, and SwiGLU configuration.
  - Add an AMD MI35x sanity/eval test for the GPT-OSS-120B MXFP4-FP8 Quark path.

## Accuracy Test 

### Server

```bash
export MODEL="amd/gpt-oss-120b-w-mxfp4-a-fp8"
export HOST="127.0.0.1"
export PORT="21000"

SGLANG_USE_AITER=1 \
SGLANG_USE_AITER_MOE_GU_ITLV=1 \
sglang serve \
  --model-path "${MODEL}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --tp 8 \
  --chunked-prefill-size 130172 \
  --max-running-requests 128 \
  --mem-fraction-static 0.85 \
  --attention-backend triton \
  --trust-remote-code
```

### Client

```bash
export MODEL="amd/gpt-oss-120b-w-mxfp4-a-fp8"
export HOST="127.0.0.1"
export PORT="21000"
export GSM8K_NUM_QUESTIONS="200"

python test/registered/amd/accuracy/mi35x/test_gpt_oss_w4a8_mxfp4_eval_mi35x.py
```

### Results

Measured with TP=8, Triton attention, AITER enabled, and `GSM8K_NUM_QUESTIONS=200`.

| Metric | Value |
| ------ | ----- |
| GSM8K accuracy | 0.845 |
| Accuracy threshold | 0.79 |
| Status | PASS |

Reference command output:

```text
accuracy=0.845 threshold=0.79 PASS
Ran 1 test in 71.464s
OK
```


## Speed Test

### Server

```bash
export MODEL="amd/gpt-oss-120b-w-mxfp4-a-fp8"
export HOST="127.0.0.1"
export PORT="9000"

SGLANG_USE_AITER=1 \
SGLANG_USE_AITER_MOE_GU_ITLV=1 \
sglang serve \
  --model-path "${MODEL}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --tp 1 \
  --chunked-prefill-size 130172 \
  --max-running-requests 128 \
  --mem-fraction-static 0.85 \
  --attention-backend triton \
  --trust-remote-code
```

### Client

```bash
export MODEL="amd/gpt-oss-120b-w-mxfp4-a-fp8"
export HOST="127.0.0.1"
export PORT="9000"
export input_tokens="8192"
export output_tokens="1024"
export random_range_ratio="1.0"
export max_concurrency="8"
export num_prompts="16"
export tmp_log="/tmp/gptoss_w4a8_tp1_${input_tokens}_${output_tokens}_c${max_concurrency}.log"

python3 -m sglang.bench_serving \
  --host "${HOST}" \
  --port "${PORT}" \
  --model "${MODEL}" \
  --dataset-name "random" \
  --random-input-len "${input_tokens}" \
  --random-output-len "${output_tokens}" \
  --random-range-ratio "${random_range_ratio}" \
  --max-concurrency "${max_concurrency}" \
  --percentile-metrics "ttft,tpot,itl,e2el" \
  --num-prompts "${num_prompts}" \
  2>&1 | tee "${tmp_log}"
```

### Results

Measured on TP=1 with input length 8192, output length 1024, max concurrency 8, and 16 prompts.

| Metric | Value |
| ------ | ----- |
| Successful requests | 16 |
| Benchmark duration | 19.21 s |
| Request throughput | 0.83 req/s |
| Input token throughput | 6824.07 tok/s |
| Output token throughput | 853.01 tok/s |
| Peak output token throughput | 1056.00 tok/s |
| Total token throughput | 7677.08 tok/s |
| Mean E2E latency | 9597.85 ms |
| Median E2E latency | 9597.62 ms |
| P90 E2E latency | 9684.15 ms |
| Mean TTFT | 1261.89 ms |
| P90 TTFT | 1761.55 ms |
| Mean TPOT | 8.15 ms |
| P90 TPOT | 8.69 ms |
| Mean ITL | 8.15 ms |
| P90 ITL | 7.90 ms |

































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28410628052](https://github.com/sgl-project/sglang/actions/runs/28410628052)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28410628012](https://github.com/sgl-project/sglang/actions/runs/28410628012)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
