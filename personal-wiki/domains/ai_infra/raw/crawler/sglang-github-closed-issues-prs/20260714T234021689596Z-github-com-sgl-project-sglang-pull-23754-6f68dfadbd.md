---
source_id: sglang-github-closed-issues-prs
title: '[Quantization] add humming quantization kernel'
canonical_url: https://github.com/sgl-project/sglang/pull/23754
captured_at: '2026-07-14T23:40:21.689596+00:00'
content_hash: 6f68dfadbde349cdc227ac2c75aa46214f087e6c2eb44e740713c8d740ecd8ad
---
# [Quantization] add humming quantization kernel

URL: https://github.com/sgl-project/sglang/pull/23754
State: closed
Labels: documentation, amd, dependencies, sgl-kernel, run-ci, diffusion, mthreads, jit-kernel, bypass-fastfail
Closed at: 2026-07-14T00:42:57Z
Merged at: 2026-07-14T00:42:57Z

This PR add humming kernels to SGLang.

coauthers: @huangzhilin-hzl @guzekai01 

Humming Kenrels: https://github.com/inclusionAI/humming

vLLM supports: https://github.com/vllm-project/vllm/pull/34556

Humming is a universal, high-performance quantization kernel (similar to the Marlin kernel), but offers several advantages over Marlin:

* Extensive Quantization Support: Supports all combinations of W{1,2,3,4,5,6,7,8}A{16,8,4} for quantization inference.
* Superior Performance: Humming outperforms Marlin, especially in large batch scenarios and on Hopper GPUs.
* Enhanced JIT Support: Compared to the current Marlin JIT implementation in SGLang, Humming offers faster compilation.
* For DeepSeek V4, Humming supports high-performance W4A8 implementation on Hopper.
* Support DeepEP 

For Chinese users, please refer to these three blog posts:
* https://zhuanlan.zhihu.com/p/2021951434141222000
* https://zhuanlan.zhihu.com/p/2031516408954234360
* https://zhuanlan.zhihu.com/p/2032065891857343604





## Benchmark Results



### Kimi-K2.6 + 8 x H20


serving command

```
# marlin
sglang serve \
  --model-path /home/admin/Kimi-K2.6 \
  --tp 8 \
  --trust-remote-code \
  --reasoning-parser kimi_k2 \
  --tool-call-parser kimi_k2 \
  --host 0.0.0.0 \
  --port 30000 \
  --disable-shared-experts-fusion \
  --mem-fraction-static 0.90 \
  --context-length 80000

# humming: with --quantization humming
# humming-w4a8: with --quantization humming and env variable SGLANG_HUMMING_INPUT_QUANT_CONFIG='{"dtype": "float8e4m3"}'
```

accuracy test command

```
python3 -m sglang.test.few_shot_gsm8k --num-questions 200
```

benchmark command

```
python3 -m sglang.bench_serving \
  --backend sglang \
  --host 127.0.0.1 \
  --port 30000 \
  --dataset-name random \
  --random-input-len xx \
  --random-output-len xx \
  --num-prompts xx \
  --max-concurrency xx

# input-len / output-len / num-prompts / max-concurrency: see result tables
```

| input-len | output | num-prompts | max-concurrency | backend | input-tok/s | output-tok/s | total-tok/s | tpot | ttft | gsm8k |
|---|---|---|---|---|---|---|---|---|---|---|
| 1024 | 1024 | 10 | 1 | marlin | 181.93 | 125.84 | 307.78 | 7.52 | 180.60 | 0.955 |
| 1024 | 1024 | 10 | 1 | humming | 185.41 | 128.25 | 313.66 | 7.47 | 138.01 | 0.965 |
| 1024 | 1024 | 10 | 1 | humming_w4a8 | 186.31 | 128.87 | 315.18 | 7.44 | 137.37 | 0.970 |
| 32768 | 128 | 10 | 1 | marlin | 5851.79 | 18.98 | 5870.77 | 8.84 | 2226.72 | 0.955 |
| 32768 | 128 | 10 | 1 | humming | 7247.60 | 23.51 | 7271.10 | 8.66 | 1714.31 | 0.965 |
| 32768 | 128 | 10 | 1 | humming_w4a8 | 8158.89 | 26.46 | 8185.35 | 8.61 | 1475.76 | 0.970 |
| 1024 | 1024 | 256 | 128 | marlin | 1401.07 | 1354.41 | 2755.48 | 78.52 | 3044.23 | 0.955 |
| 1024 | 1024 | 256 | 128 | humming | 1613.46 | 1559.72 | 3173.18 | 66.17 | 2700.48 | 0.965 |
| 1024 | 1024 | 256 | 128 | humming_w4a8 | 1704.79 | 1648.01 | 3352.80 | 61.44 | 2487.79 | 0.970 |
| 32768 | 128 | 256 | 128 | marlin | 5483.90 | 23.22 | 5507.12 | 404.03 | 255399.80 | 0.955 |
| 32768 | 128 | 256 | 128 | humming | 7151.83 | 30.28 | 7182.11 | 305.18 | 195809.14 | 0.965 |
| 32768 | 128 | 256 | 128 | humming_w4a8 | 8439.19 | 35.73 | 8474.92 | 259.76 | 166175.49 | 0.970 |




### DeepSeek-V4-Flash + 4 x H20


serving command


- use command from cookbook https://lmsysorg.mintlify.app/cookbook/autoregressive/DeepSeek/DeepSeek-V4#3-1-basic-configuration
  - **low-latency**: eagle spec (steps=3, topk=1, draft=4)
  - **balanced**: eagle spec (steps=1, topk=1, draft=2)
  - **max-throughput**: no spec
- with different backend
  - **marlin**: `--moe-runner-backend marlin`
  - **flashinfer_mxfp4**: `--moe-runner-backend flashinfer_mxfp4`
  - **humming**: `--moe-runner-backend humming`
  - **humming**: `--moe-runner-backend humming` + env variable SGLANG_HUMMING_INPUT_QUANT_CONFIG='{"dtype": "float8e4m3"}'


accuracy test command

```
python3 -m sglang.test.few_shot_gsm8k --num-questions 200
```

benchmark command

```
python3 -m sglang.bench_serving \
  --backend sglang \
  --host 127.0.0.1 \
  --port 30000 \
  --dataset-name random \
  --random-input-len xx \
  --random-output-len xx \
  --num-prompts xx \
  --max-concurrency xx

# input-len / output-len / num-prompts / max-concurrency: see result tables
```


| recipe | input-len | output | num-prompts | max-concurrency | backend | input-tok/s | output-tok/s | total-tok/s | tpot | ttft | gsm8k |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| low_latency | 1024 | 1024 | 10 | 1 | marlin | 333.22 | 230.49 | 563.71 | 3.87 | 176.81 | 0.965 |
| low_latency | 1024 | 1024 | 10 | 1 | flashinfer_mxfp4 | 310.27 | 214.61 | 524.87 | 4.27 | 150.53 | 0.965 |
| low_latency | 1024 | 1024 | 10 | 1 | humming | 351.12 | 242.87 | 593.99 | 3.63 | 177.80 | 0.975 |
| low_latency | 1024 | 1024 | 10 | 1 | humming_w4a8 | 358.29 | 247.82 | 606.11 | 3.58 | 172.49 | 0.970 |
| low_latency | 32768 | 128 | 10 | 1 | marlin | 8927.96 | 28.96 | 8956.92 | 4.77 | 1538.86 | 0.965 |
| low_latency | 32768 | 128 | 10 | 1 | flashinfer_mxfp4 | 8764.96 | 28.43 | 8793.39 | 5.51 | 1554.91 | 0.965 |
| low_latency | 32768 | 128 | 10 | 1 | humming | 11274.81 | 36.57 | 11311.38 | 4.95 | 1195.74 | 0.975 |
| low_latency | 32768 | 128 | 10 | 1 | humming_w4a8 | 12730.60 | 41.29 | 12771.89 | 4.49 | 1032.82 | 0.970 |
| balanced | 1024 | 1024 | 64 | 32 | marlin | 1368.73 | 1293.65 | 2662.38 | 19.74 | 1138.21 | 0.970 |
| balanced | 1024 | 1024 | 64 | 32 | flashinfer_mxfp4 | 1261.20 | 1192.01 | 2453.21 | 21.74 | 1106.20 | 0.970 |
| balanced | 1024 | 1024 | 64 | 32 | humming | 1431.06 | 1352.56 | 2783.62 | 19.28 | 895.81 | 0.975 |
| balanced | 1024 | 1024 | 64 | 32 | humming_w4a8 | 1568.70 | 1482.65 | 3051.35 | 17.60 | 816.20 | 0.970 |
| balanced | 32768 | 128 | 64 | 32 | marlin | 8375.65 | 29.32 | 8404.97 | 1251.39 | 16119.70 | 0.970 |
| balanced | 32768 | 128 | 64 | 32 | flashinfer_mxfp4 | 8278.36 | 28.98 | 8307.33 | 1352.50 | 15484.43 | 0.970 |
| balanced | 32768 | 128 | 64 | 32 | humming | 10885.74 | 38.10 | 10923.84 | 1028.94 | 11806.41 | 0.975 |
| balanced | 32768 | 128 | 64 | 32 | humming_w4a8 | 12492.57 | 43.73 | 12536.30 | 882.87 | 11227.04 | 0.970 |
| max_throughput | 1024 | 1024 | 512 | 128 | marlin | 2005.92 | 2037.08 | 4043.00 | 56.46 | 1498.67 | 0.965 |
| max_throughput | 1024 | 1024 | 512 | 128 | flashinfer_mxfp4 | 1891.27 | 1920.65 | 3811.93 | 59.61 | 1464.35 | 0.970 |
| max_throughput | 1024 | 1024 | 512 | 128 | humming | 1930.08 | 1960.07 | 3890.15 | 59.06 | 1307.30 | 0.965 |
| max_throughput | 1024 | 1024 | 512 | 128 | humming_w4a8 | 2221.04 | 2255.54 | 4476.58 | 51.04 | 1161.43 | 0.970 |
| max_throughput | 32768 | 128 | 512 | 128 | marlin | 8414.60 | 32.80 | 8447.41 | 1657.37 | 141855.46 | 0.965 |
| max_throughput | 32768 | 128 | 512 | 128 | flashinfer_mxfp4 | 8337.61 | 32.50 | 8370.11 | 2118.80 | 122608.13 | 0.970 |
| max_throughput | 32768 | 128 | 512 | 128 | humming | 10782.03 | 42.03 | 10824.06 | 1640.60 | 91431.28 | 0.965 |
| max_throughput | 32768 | 128 | 512 | 128 | humming_w4a8 | 12858.59 | 50.13 | 12908.72 | 1364.23 | 78393.59 | 0.970 |






































































































































































































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29265329699](https://github.com/sgl-project/sglang/actions/runs/29265329699)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29265328851](https://github.com/sgl-project/sglang/actions/runs/29265328851)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
