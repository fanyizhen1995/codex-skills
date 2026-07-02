---
source_id: sglang-github-closed-issues-prs
title: '[Perf][Kernel] Fuse SiLU+Mul into NVFP4 Expert Quantization for CUTLASS MoE'
canonical_url: https://github.com/sgl-project/sglang/pull/18612
captured_at: '2026-07-01T02:12:08.971389+00:00'
content_hash: 7bb3bf6a1b87318d569a0fd48e46f05d2637f1d2d9ea777abf1f7fa67267a55a
---
# [Perf][Kernel] Fuse SiLU+Mul into NVFP4 Expert Quantization for CUTLASS MoE

URL: https://github.com/sgl-project/sglang/pull/18612
State: closed
Labels: quant, sgl-kernel, blackwell, run-ci, jit-kernel
Closed at: 2026-06-29T23:51:02Z
Merged at: 2026-06-29T23:51:02Z

## Summary
In the CUTLASS FP4 MoE pipeline, the path between GEMM1 and GEMM2 previously required **3 separate steps**: allocate intermediate buffer → `silu_and_mul` → `scaled_fp4_experts_quant`. This PR fuses them into a **single CUDA kernel** `silu_and_mul_scaled_fp4_experts_quant_packed`, eliminating one intermediate buffer allocation and one extra kernel launch. Inspired by vllm [#31832](https://github.com/vllm-project/vllm/pull/31832)


## Before → After this PR
```
# Before (3 steps, 1 extra buffer)
intermediate = torch.empty((m*topk, k//2), ...)   # alloc
silu_and_mul(c1, intermediate)                      # kernel 1
int_fp4, scales = scaled_fp4_experts_quant(intermediate, ...)  # kernel 2

# After (1 step, no intermediate buffer)
int_fp4, scales = silu_and_mul_scaled_fp4_experts_quant_packed(c1, ...)  # fused kernel
```

## Key Changes
**CUDA kernel** ([nvfp4_expert_quant.cu](vscode-file://vscode-app/Applications/Visual%20Studio%20Code.app/Contents/Resources/app/out/vs/code/electron-browser/workbench/workbench.html)):
- Added `use_silu_and_mul` flag to `cvt_fp16_to_fp4` kernels (both low-latency and offset-based variants). Previously SiLU+mul was implicitly tied to `mask != nullptr`; now it's an independent toggle.
- New entry function `silu_and_mul_scaled_fp4_experts_quant_packed_sm100a` — uses **expert offsets** (not masks) to correctly handle non-uniform token distribution across experts.
- Input shape `(m, 2*k)` — gate+up concatenated from GEMM1 output; the kernel reads both halves, applies SiLU(gate)×up, then FP4-quantizes in one pass.

**Op registration** ([common_extension.cc](vscode-file://vscode-app/Applications/Visual%20Studio%20Code.app/Contents/Resources/app/out/vs/code/electron-browser/workbench/workbench.html), [sgl_kernel_ops.h](vscode-file://vscode-app/Applications/Visual%20Studio%20Code.app/Contents/Resources/app/out/vs/code/electron-browser/workbench/workbench.html), [nvfp4_quant_entry.cu](vscode-file://vscode-app/Applications/Visual%20Studio%20Code.app/Contents/Resources/app/out/vs/code/electron-browser/workbench/workbench.html)):
- Registered `silu_and_mul_scaled_fp4_experts_quant_packed` as a new torch op.

**Python wrapper** ([gemm.py](vscode-file://vscode-app/Applications/Visual%20Studio%20Code.app/Contents/Resources/app/out/vs/code/electron-browser/workbench/workbench.html)):
- `silu_and_mul_scaled_fp4_experts_quant_packed()` — handles dimension calculation (`k = input.shape[1] // 2`), output/scale allocation, kernel dispatch, and reinterprets scale output as `float8_e4m3fn` for GEMM2.

**MoE integration** ([cutlass_moe.py](vscode-file://vscode-app/Applications/Visual%20Studio%20Code.app/Contents/Resources/app/out/vs/code/electron-browser/workbench/workbench.html)):
- Replaced the 3-step unfused path with single `silu_and_mul_scaled_fp4_experts_quant_packed(c1, ...)` call.

**Unit test** (test_silu_and_mul_scaled_fp4_experts_quant_packed.py):
- Added a UT comparing the fused op against the unfused `silu_and_mul` + `scaled_fp4_experts_quant` path with **uneven expert offsets** — asserts bit-identical packed FP4 nibbles and block scales per expert, grounded against an fp32 `SiLU(gate)×up` reference (12 cases). Also includes a CUDA-graph perf check (~1.28–1.42× at 1k–16k tokens, Qwen3-30B-A3B MoE dims).

## Experimental Results

Experimental Setup
```
HW: GB200*4
Model: nvidia/Qwen3-30B-A3B-NVFP4
Run: 
python3 -m sglang.launch_server --model-path /data06/models/Qwen3-30B-A3B-NVFP4  --trust-remote-code --port 8010 --mem-fraction-static 0.90 --disable-radix-cache
```

### Accuracy & Throughput & Latency Benchmark
 Both latency and throughput brings  ~5% improvement
``` 
$ python3 benchmark/gsm8k/bench_sglang.py --num-shots 8 --port 8010

# Base
Accuracy: 0.910
Invalid: 0.000
Latency: 13.969 s
Output throughput: 1840.902 token/s

# PR
Accuracy: 0.910
Invalid: 0.000
Latency: 13.298 s
Output throughput: 1933.693 token/s
```

### Throughput Benchmark
1.4% gain
```
python3 -m sglang.bench_serving --backend sglang-oai-chat --base-url http://127.0.0.1:8010 --model /data06/models/Qwen3-30B-A3B-NVFP4 --dataset-name random --seed 5 --random-input-len 3500 --random-output-len 1500 --num-prompts 512

# Baseline
============ Serving Benchmark Result ============
Backend:                                 sglang-oai-chat
Traffic request rate:                    inf
Max request concurrency:                 not set
Successful requests:                     512
Benchmark duration (s):                  33.99
Total input tokens:                      873513
Total input text tokens:                 873513
Total generated tokens:                  384805
Total generated tokens (retokenized):    383474
Request throughput (req/s):              15.06
Input token throughput (tok/s):          25700.15
Output token throughput (tok/s):         11321.58
Peak output token throughput (tok/s):    25225.00
Peak concurrent requests:                512
Total token throughput (tok/s):          37021.74
Concurrency:                             361.26
----------------End-to-End Latency----------------
Mean E2E Latency (ms):                   23981.91
Median E2E Latency (ms):                 25144.01
P90 E2E Latency (ms):                    32213.33
P99 E2E Latency (ms):                    33801.63
---------------Time to First Token----------------
Mean TTFT (ms):                          5709.78
Median TTFT (ms):                        5503.59
P99 TTFT (ms):                           10230.33
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          38.04
Median TPOT (ms):                        24.75
P99 TPOT (ms):                           256.45
---------------Inter-Token Latency----------------
Mean ITL (ms):                           24.40
Median ITL (ms):                         18.42
P95 ITL (ms):                            21.63
P99 ITL (ms):                            26.44
Max ITL (ms):                            8364.16
==================================================

# PR
============ Serving Benchmark Result ============
Backend:                                 sglang-oai-chat
Traffic request rate:                    inf
Max request concurrency:                 not set
Successful requests:                     512
Benchmark duration (s):                  33.52
Total input tokens:                      873513
Total input text tokens:                 873513
Total generated tokens:                  384805
Total generated tokens (retokenized):    383470
Request throughput (req/s):              15.28
Input token throughput (tok/s):          26062.39
Output token throughput (tok/s):         11481.16
Peak output token throughput (tok/s):    24969.00
Peak concurrent requests:                512
Total token throughput (tok/s):          37543.55
Concurrency:                             362.60
----------------End-to-End Latency----------------
Mean E2E Latency (ms):                   23736.42
Median E2E Latency (ms):                 25363.32
P90 E2E Latency (ms):                    31750.16
P99 E2E Latency (ms):                    33325.78
---------------Time to First Token----------------
Mean TTFT (ms):                          5464.31
Median TTFT (ms):                        5269.75
P99 TTFT (ms):                           9846.33
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          37.91
Median TPOT (ms):                        24.83
P99 TPOT (ms):                           252.14
---------------Inter-Token Latency----------------
Mean ITL (ms):                           24.40
Median ITL (ms):                         18.83
P95 ITL (ms):                            22.13
P99 ITL (ms):                            26.22
Max ITL (ms):                            8306.58
==================================================
```

### Latency Benchmark
2% gain
```
python3 -m sglang.bench_serving --backend sglang-oai-chat --base-url http://127.0.0.1:8010 --model /data06/models/Qwen3-30B-A3B-NVFP4 --dataset-name random --seed 5 --random-input-len 100 --random-output-len 100 --num-prompts 8


# baseline 
============ Serving Benchmark Result ============
Backend:                                 sglang-oai-chat
Traffic request rate:                    inf
Max request concurrency:                 not set
Successful requests:                     8
Benchmark duration (s):                  0.67
Total input tokens:                      432
Total input text tokens:                 432
Total generated tokens:                  376
Total generated tokens (retokenized):    376
Request throughput (req/s):              11.95
Input token throughput (tok/s):          645.33
Output token throughput (tok/s):         561.67
Peak output token throughput (tok/s):    376.00
Peak concurrent requests:                8
Total token throughput (tok/s):          1207.00
Concurrency:                             5.20
----------------End-to-End Latency----------------
Mean E2E Latency (ms):                   435.32
Median E2E Latency (ms):                 408.65
P90 E2E Latency (ms):                    659.82
P99 E2E Latency (ms):                    660.35
---------------Time to First Token----------------
Mean TTFT (ms):                          129.90
Median TTFT (ms):                        129.97
P99 TTFT (ms):                           130.63
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          6.57
Median TPOT (ms):                        6.63
P99 TPOT (ms):                           6.84
---------------Inter-Token Latency----------------
Mean ITL (ms):                           6.64
Median ITL (ms):                         6.58
P95 ITL (ms):                            7.31
P99 ITL (ms):                            8.71
Max ITL (ms):                            8.99
==================================================

# PR
============ Serving Benchmark Result ============
Backend:                                 sglang-oai-chat
Traffic request rate:                    inf
Max request concurrency:                 not set
Successful requests:                     8
Benchmark duration (s):                  0.66
Total input tokens:                      432
Total input text tokens:                 432
Total generated tokens:                  376
Total generated tokens (retokenized):    376
Request throughput (req/s):              12.21
Input token throughput (tok/s):          659.11
Output token throughput (tok/s):         573.67
Peak output token throughput (tok/s):    376.00
Peak concurrent requests:                8
Total token throughput (tok/s):          1232.78
Concurrency:                             5.20
----------------End-to-End Latency----------------
Mean E2E Latency (ms):                   426.12
Median E2E Latency (ms):                 400.27
P90 E2E Latency (ms):                    646.16
P99 E2E Latency (ms):                    646.77
---------------Time to First Token----------------
Mean TTFT (ms):                          125.13
Median TTFT (ms):                        125.19
P99 TTFT (ms):                           125.78
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          6.48
Median TPOT (ms):                        6.52
P99 TPOT (ms):                           6.78
---------------Inter-Token Latency----------------
Mean ITL (ms):                           6.54
Median ITL (ms):                         6.49
P95 ITL (ms):                            7.20
P99 ITL (ms):                            7.53
Max ITL (ms):                            7.54
==================================================
```


## Unit Test

A new unit test was added:
`test/registered/jit/tests/test_silu_and_mul_scaled_fp4_experts_quant_packed.py`

### What it stress-tests

It compares the new fused op `silu_and_mul_scaled_fp4_experts_quant_packed`
against the exact unfused path it replaces — `silu_and_mul` followed by
`scaled_fp4_experts_quant` — **with uneven expert offsets**: experts are given
deliberately non-uniform token counts (tiny experts, an exactly-128-row expert,
and experts that straddle the 128-row block-scale padding). This is precisely the
regime that exercises the per-expert `expert_offsets` / `blockscale_offsets`
indexing that the fusion has to get right. It follows the existing siblings
`test_nvfp4_blockwise_moe` and `test_silu_and_mul_quantize_to_fp4_grouped`.

### How to run UT

```bash
$ pytest test/registered/jit/tests/test_silu_and_mul_scaled_fp4_experts_quant_packed.py -v
# add -s to also print the per-shape perf numbers
```

### UT Correctness

For every expert (honoring the uneven offsets), the test asserts:

- the packed FP4 nibbles are **bit-identical** between fused and unfused (0 mismatched bytes measured), and
- the de-swizzled block scales are **bit-identical** (0 diff measured), and
- both paths reproduce a high-precision fp32 `F.silu(gate) * up` reference within FP4 error (`rel_l2 ≈ 0.09`, well under the `0.2` tolerance) — this grounding prevents a bug shared by both kernels from passing vacuously.

Parametrized over 3 uneven layouts × `n ∈ {256, 768}` × `{bf16, fp16}` = **12 cases, all passing**.

### UT Performance

Isolated fused-vs-unfused step, measured under CUDA graphs (steady-state, matching graphed decode) at Qwen3-30B-A3B MoE dims (`n=768`, 128 experts):

| tokens | speedup |
|---:|:---:|
| 1024  | 1.36× |
| 4096  | 1.42× |
| 16384 | 1.28× |

The test also asserts a conservative regression floor so the fusion cannot silently become slower.

### UT Summary

The fused op is a drop-in, **bit-exact** replacement for the unfused
`silu_and_mul + scaled_fp4_experts_quant` path — verified under uneven expert
offsets — while delivering **1.28–1.42×** on the isolated SiLU+mul+NVFP4-quant step
(tokens=1k–16k, Qwen3-30B-A3B MoE dims) by removing one buffer allocation, one
kernel launch, and a full HBM round-trip of the intermediate.



## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review Process

1. Ping Merge Oncalls to start the PR flow. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - `/tag-run-ci-label`, `/rerun-failed-ci`, `/tag-and-rerun-ci`
4. After green CI and required approvals, ask Merge Oncalls to merge.


































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28331919487](https://github.com/sgl-project/sglang/actions/runs/28331919487)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28331919441](https://github.com/sgl-project/sglang/actions/runs/28331919441)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
