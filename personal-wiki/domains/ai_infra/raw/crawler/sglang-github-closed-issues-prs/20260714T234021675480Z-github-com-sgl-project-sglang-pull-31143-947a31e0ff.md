---
source_id: sglang-github-closed-issues-prs
title: '[AMD] jit_kernel: complete utils.cuh HIP-compat (cudaDevAttr / cudaDeviceGetAttribute)'
canonical_url: https://github.com/sgl-project/sglang/pull/31143
captured_at: '2026-07-14T23:40:21.675480+00:00'
content_hash: 947a31e0ff790872e5f31f52c7ac68be534db58f070b24b7ef3f99d24d5a4069
---
# [AMD] jit_kernel: complete utils.cuh HIP-compat (cudaDevAttr / cudaDeviceGetAttribute)

URL: https://github.com/sgl-project/sglang/pull/31143
State: closed
Labels: jit-kernel
Closed at: 2026-07-14T08:06:37Z
Merged at: 2026-07-14T08:06:37Z

## Motivation

The JIT kernels' shared header `jit_kernel/include/sgl_kernel/utils.cuh` has a HIP-compat block (mapping `cudaGetErrorString`, `cudaMemcpy*`, …) but is **missing** `cudaDeviceGetAttribute` and the `cudaDevAttrComputeCapabilityMajor/Minor` enums that its own `getSMVersion()` uses. On ROCm this makes any JIT kernel that includes `utils.cuh` — e.g. the KV-cache kernel every model compiles — fail to build:

```
utils.cuh:245: error: use of undeclared identifier 'cudaDevAttrComputeCapabilityMajor'
ninja: build stopped: subcommand failed.
```

The sibling `jit_kernel/include/sgl_kernel/runtime.cuh` already defines these exact mappings; `utils.cuh` simply lacked them. It surfaces on **RDNA / gfx1151** (Strix Halo) because CDNA's AITER path skips these JIT kernels — so on gfx1151, stock `main` can't currently serve any model until this is fixed.

Companion to https://github.com/sgl-project/sglang/pull/31137 (the `sgl-kernel` gfx1151 build enablement): that PR makes `sgl-kernel` build; this one makes the JIT path compile so a model actually serves. Part of the consumer-RDNA enablement tracked in #30599.

## Modifications

`jit_kernel/include/sgl_kernel/utils.cuh` — three `#define`s added to the existing `#else /* USE_ROCM */` HIP-compat block:

```
#define cudaDeviceGetAttribute hipDeviceGetAttribute
#define cudaDevAttrComputeCapabilityMajor hipDeviceAttributeComputeCapabilityMajor
#define cudaDevAttrComputeCapabilityMinor hipDeviceAttributeComputeCapabilityMinor
```

They're inside the `USE_ROCM` guard, so the **CUDA build is byte-identical**. No other files.

## Accuracy Tests

No numerics change (a build-time HIP symbol mapping). gfx1151 correctness is unaffected — e.g. Qwen2.5-7B GSM8K stays at 92% (matrix in https://github.com/sgl-project/sglang/pull/31137).

## Speed Tests and Profiling

N/A — build-time compat fix; no kernel or runtime change.

## Test plan — real gfx1151 (RDNA3.5), current `main` + https://github.com/sgl-project/sglang/pull/31137

Without this fix, serving any model fails at JIT compile (`ninja` status 1, undeclared `cudaDevAttrComputeCapabilityMajor`). With it, current `main` serves end-to-end:

| Model | Type | Result |
|---|---|---|
| Qwen2.5-7B | dense | ✅ ready, correct, 0 hipError |
| OLMoE-1B-7B | MoE | ✅ ready, correct, 0 hipError |

```bash
python -m sglang.launch_server --model-path Qwen/Qwen2.5-7B-Instruct \
  --attention-backend triton --mem-fraction-static 0.5   # add --disable-cuda-graph for MoE
```

## Checklist

- [x] Format with pre-commit (clang-format green).
- [ ] Add unit tests — N/A (a preprocessor HIP-compat mapping; no testable product surface).
- [ ] Update documentation — N/A.
- [ ] Accuracy/speed benchmarks — N/A (no numerics/perf change; end-to-end serve verified above).
- [x] Follow the SGLang code style guidance.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29315743318](https://github.com/sgl-project/sglang/actions/runs/29315743318)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29315743048](https://github.com/sgl-project/sglang/actions/runs/29315743048)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
