---
source_id: sglang-github-closed-issues-prs
title: '[DSV4][Perf] Fuse FP8 quantization with DSV4 scale layout write'
canonical_url: https://github.com/sgl-project/sglang/pull/28944
captured_at: '2026-07-08T23:36:33.802705+00:00'
content_hash: 28dea6c0087baedaf58d15949f4635a999f62f41d5a1fc8b8a9169cec276f6e5
---
# [DSV4][Perf] Fuse FP8 quantization with DSV4 scale layout write

URL: https://github.com/sgl-project/sglang/pull/28944
State: closed
Labels: quant, deepseek, run-ci, jit-kernel, run-ci-extra
Closed at: 2026-07-08T02:04:51Z
Merged at: 

## Summary

This is the follow-up/rebase of my earlier DSV4 FP8 `wo_a` fusion work from #27818.

Since then, main already picked up part of the idea: UE8M0 scale rounding is now fused into the generic JIT v2 FP8 group quant path. So this PR is a smaller delta than #27818. It keeps the current main behavior for `scale_ue8m0=True`, but still removes the remaining DSV4-specific extra scale layout materialization.

The DSV4 `wo_a` path needs activation scales in the layout used by:

```python
deep_gemm.fp8_einsum("bhr,hdr->bhd", ...)
```

Before this PR, we quantized with the generic path and then reshaped/transposed the scale tensor into the final DSV4 layout. This PR writes that final layout directly from the quantization kernel.

## Changes

- Added a DSV4-specific JIT v2 entry: `PerTokenGroupQuantFp8Dsv4Kernel`.
- Added Python wrapper `per_token_group_quant_fp8_dsv4`.
- Added helper `sglang_per_token_group_quant_fp8_dsv4_ue8m0`.
- Routed the DeepSeek-V4 FP8 `wo_a` path through the new helper.
- Added a registered DSV4 test for BF16/FP16, empty/non-empty inputs, exact FP8 bytes, exact scale values, and final scale tensor shape/stride.

One detail compared with #27818: the old PR preserved the old FP8 bytes and rounded only the stored scale. This version follows current main: FP8 quantization itself uses the rounded power-of-two UE8M0 scale, so it is bit-exact with the current generic `scale_ue8m0=True` path plus the old DSV4 layout transform.

## Accuracy

### GSM8K

Server:

```bash
CUDA_VISIBLE_DEVICES=3 \
python -m sglang.launch_server \
  --trust-remote-code \
  --model-path deepseek-ai/DeepSeek-V4-Flash \
  --moe-runner-backend flashinfer_mxfp4 \
  --disable-flashinfer-autotune \
  --model-loader-extra-config '{"enable_multithread_load": true, "num_threads": 46}'
```

Benchmark:

```bash
sgl-eval run \
  --base-url http://127.0.0.1:30000/v1 \
  --num-threads 256 \
  gsm8k
```

Results:

| benchmark | examples | score | latency | output throughput |
|---|---:|---:|---:|---:|
| GSM8K | 1319 | 96.89% | 81.7s | 1766 tok/s |

## Perf

Benchmarks were run on one GPU from a GB300 node.

### Bench Serving, 8192 / 1024

Server:

```bash
CUDA_VISIBLE_DEVICES=3 \
python -m sglang.launch_server \
  --trust-remote-code \
  --model-path deepseek-ai/DeepSeek-V4-Flash \
  --moe-runner-backend flashinfer_mxfp4 \
  --disable-flashinfer-autotune \
  --model-loader-extra-config '{"enable_multithread_load": true, "num_threads": 46}'
```

Benchmark:

```bash
python -m sglang.bench_serving \
  --model deepseek-ai/DeepSeek-V4-Flash \
  --dataset-name random \
  --random-input-len 8192 \
  --random-output-len 1024 \
  --random-range-ratio 1.0 \
  --max-concurrency 16 \
  --num-prompts 64 \
  --flush-cache
```

Results:

| Metric | Baseline | This PR | Delta |
|---|---:|---:|---:|
| Output throughput | 620.55 tok/s | 748.96 tok/s | **+20.7%** |
| Mean TTFT | 3863.19 ms | 2643.26 ms | **31.6% faster** |
| Mean TPOT | 22.02 ms | 18.79 ms | **14.7% faster** |





























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #27960005882](https://github.com/sgl-project/sglang/actions/runs/27960005882)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #27960416907](https://github.com/sgl-project/sglang/actions/runs/27960416907)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
