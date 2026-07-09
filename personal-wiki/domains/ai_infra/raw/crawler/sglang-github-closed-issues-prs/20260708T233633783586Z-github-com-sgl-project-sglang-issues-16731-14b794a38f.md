---
source_id: sglang-github-closed-issues-prs
title: What is the current optimal performance for DeepSeek-V3.2 in PD-separated deployment?
canonical_url: https://github.com/sgl-project/sglang/issues/16731
captured_at: '2026-07-08T23:36:33.783586+00:00'
content_hash: 14b794a38f815b86a1e4a26d9860e896a15b1a7c003ebb278b5c9e4cd94f514d
---
# What is the current optimal performance for DeepSeek-V3.2 in PD-separated deployment?

URL: https://github.com/sgl-project/sglang/issues/16731
State: closed
Labels: inactive
Closed at: 2026-07-08T00:34:33Z
Merged at: 

I'm currently benchmarking **DeepSeek-V3.2** using **PD-separated deployment** (P: 2 node / 16x H800, D: 4 nodes / 32x H800 total, 4 RDMA NIC/node with mooncake-transfer-engin 0.3.7.post2) via SGLang(the latest main branch at datetime 20260105), and I'd like to understand what the expected or community-achieved optimal performance is for this model configuration.
#### My Setup:
- **Model**: `DeepSeek-V3.2`
- **Deployment**: PD separation
  - **Prefill (P)**: 2 node, 16× H800
  - **Decode (D)**: 4 nodes, 32× H800 (total)
- **Framework**: SGLang
- **Client**: `sglang.bench_serving`

#### Benchmark Results:

**Test 1 (Prefill):**
```bash
python -m sglang.bench_serving \
  --backend sglang \
  --dataset-name random \
  --dataset-path /home/logs/ShareGPT_V3_unfiltered_cleaned_split/ShareGPT_V3_unfiltered_cleaned_split.json \
  --random-input 4096 \
  --random-output 5 \
  --random-range-ratio 1 \
  --request-rate 1 \
  --num-prompts 200 \
  --output-file "/home/logs/dpskv32.json" \
  --host 127.0.0.1 \
  --port 8000 \
  --model /home/DeepSeek-V3.2
```
Result:
```
Request throughput (req/s):    1.02  
Input token throughput (tok/s): 4167.37  
Concurrency:                     2.69  
Mean TTFT (ms):                  2429.84  
Median TTFT (ms):                1916.53  
P99 TTFT (ms):                   10865.97
```
→ Achieved: ~2k input tokens/sec per prefill node (toooo slow maybe)

**Test 2 (Decode):**
```bash
python -m sglang.bench_serving \
  --backend sglang \
  --dataset-name random \
  --dataset-path /home/logs/ShareGPT_V3_unfiltered_cleaned_split/ShareGPT_V3_unfiltered_cleaned_split.json \
  --random-input 1024 \
  --random-output 1024 \
  --random-range-ratio 1 \
  --request-rate 64 \
  --max-concurrency 1024 \
  --num-prompts 2048 \
  --output-file "/home/logs/dpskv32.json" \
  --host 127.0.0.1 \
  --port 8000 \
  --model /home/DeepSeek-V3.2
```
Result:

<img width="3820" height="630" alt="Image" src="https://github.com/user-attachments/assets/42d9776f-413a-4e37-b687-ffc8dad5713c" />

→ Achieved: ~3k input tokens/sec per decode node


Could you please share:
* What is the current known optimal performance (in terms of input token throughput per decode node) for DeepSeek-V3.2 under PD-separated deployment?
* Are there any recommended configurations (e.g., batch size, tensor parallelism, context scheduling, or runtime settings in SGLang) that can help achieve higher throughput?
* Is this gap from prior results possibly due to changes in SGLang version, model loading, or kernel optimizations?
We want to make sure we're not missing any recent best practices or tuning knobs.

My deployment params is as follows:

```
python3 -m sglang.launch_server \
  --model-path /home/DeepSeek-V3.2 \
  --host 33.205.171.217 \
  --port 30000 \
  --dist-init-addr 33.205.171.217:5000 \
  --trust-remote-code \
  --nnodes 2 \
  --node-rank 0 \
  --disaggregation-mode prefill \
  --disaggregation-ib-device mlx5_4,mlx5_20,mlx5_26,mlx5_34 \
  --disaggregation-bootstrap-port 8998 \
  --page-size 64 \
  --tp-size 16 \
  --dp-size 16 \
  --ep-size 16 \
  --load-balance-method round_robin \
  --enable-dp-attention \
  --enable-dp-lm-head \
  --moe-a2a-backend deepep \
  --moe-dense-tp-size 1 \
  --deepep-mode normal \
  --enable-eplb \
  --max-running-requests 512 \
  --max-prefill-tokens 2048 \
  --chunked-prefill-size 32768 \
  --context-len 65536 \
  --mem-fraction-static 0.806 \
  --enable-two-batch-overlap \
  --decode-log-interval 10 \
  --reasoning-parser deepseek-v3 \
  --tool-call-parser deepseekv32 \
  --enable-metrics \
  --collect-tokens-histogram \
  --attention-backend nsa \
  --nsa-prefill-backend flashmla_sparse
```

```
python3 -m sglang.launch_server \
  --model-path /home/DeepSeek-V3.2 \
  --host 33.205.160.39 \
  --port 30000 \
  --dist-init-addr 33.205.160.39:5000 \
  --trust-remote-code \
  --nnodes 4 \
  --node-rank 0 \
  --disaggregation-mode decode \
  --disaggregation-ib-device mlx5_5,mlx5_21,mlx5_27,mlx5_36 \
  --disaggregation-bootstrap-port 8998 \
  --page-size 64 \
  --tp-size 32 \
  --dp-size 32 \
  --ep-size 32 \
  --prefill-round-robin-balance \
  --enable-dp-attention \
  --enable-dp-lm-head \
  --moe-a2a-backend deepep \
  --moe-dense-tp-size 1 \
  --deepep-mode low_latency \
  --enable-eplb \
  --ep-num-redundant-experts 32 \
  --ep-dispatch-algorithm dynamic \
  --max-running-requests 1024 \
  --context-len 65536 \
  --mem-fraction-static 0.82 \
  --enable-two-batch-overlap \
  --disable-radix-cache \
  --decode-log-interval 10 \
  --cuda-graph-max-bs 64 \
  --cuda-graph-bs 1 2 4 8 16 32 40 64 \
  --reasoning-parser deepseek-v3 \
  --tool-call-parser deepseekv32 \
  --enable-metrics \
  --collect-tokens-histogram \
  --attention-backend nsa \
  --nsa-decode-backend fa3 \
  --disable-tokenizer-batch-decode
```
