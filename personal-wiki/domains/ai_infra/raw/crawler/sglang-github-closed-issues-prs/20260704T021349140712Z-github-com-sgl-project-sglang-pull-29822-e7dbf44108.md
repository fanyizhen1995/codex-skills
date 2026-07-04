---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Accept ROCm tensors in JIT kernel TensorMatcher + register 4 kernel
  tests'
canonical_url: https://github.com/sgl-project/sglang/pull/29822
captured_at: '2026-07-04T02:13:49.140712+00:00'
content_hash: e7dbf44108940ba4da56dcc64f5a255ef9502ee1f14e1a96151ea0f429a0dd45
---
# [AMD] Accept ROCm tensors in JIT kernel TensorMatcher + register 4 kernel tests

URL: https://github.com/sgl-project/sglang/pull/29822
State: closed
Labels: run-ci, jit-kernel, bypass-fastfail
Closed at: 2026-07-03T02:29:48Z
Merged at: 2026-07-03T02:29:48Z

## Motivation

The upstream-CI coverage dashboard's **Kernel** tier (JIT kernels, separate AMD path) shows AMD registers only a fraction of the NVIDIA JIT kernel tests. Simply adding `register_amd_ci(...)` to most `test/registered/jit/` files does **not** work — the tests fail on ROCm at runtime with:

```
RuntimeError: Tensor match failed ... at .../jit_kernel/csrc/add_constant.cuh
- Root cause: Device value [rocm:0] not in the allowed options: [cuda]
```

The JIT kernels validate tensors with `TensorMatcher.with_device<kDLCUDA>()`, which restricts the allowed device type to `kDLCUDA` only. On ROCm builds PyTorch / tvm-ffi tag GPU tensors as `kDLROCM`, so the device check rejects every HIP tensor. This is a key blocker to expanding AMD JIT-kernel coverage.

## Changes

**1. Use the platform-aware `kDLGPU` alias in AMD-supported kernels**

`utils.cuh` already defines `kDLGPU` (`kDLCUDA` on CUDA, `kDLROCM` on ROCm). For the kernels we want to run on AMD, switch the device checks from `kDLCUDA` to `kDLGPU`:

- `csrc/add_constant.cuh`
- `csrc/ngram_embedding.cuh`
- `csrc/diffusion/causal_conv3d_cat_pad.cuh`

CUDA behavior is byte-identical (`kDLGPU == kDLCUDA` there); on ROCm the same kernels now validate HIP tensors. This is an explicit per-kernel opt-in rather than a global change to `kDLCUDA` semantics (thanks @DarkSharpness for the suggestion).

**2. Register the JIT kernel tests that now pass on AMD** for the per-PR `jit-kernel-unit-test-amd` suite:

| File | `est_time` |
|---|---|
| `test/registered/jit/test_add_constant.py` | 8 |
| `test/registered/jit/test_ngram_embedding.py` | 8 |
| `test/registered/jit/diffusion/test_causal_conv3d_cat_pad.py` | 10 |

## Test plan

Verified locally on **MI355X (gfx950, ROCm 7.2)** with a cleared JIT cache: the newly-registered files pass **62/62** combined, and an already-registered AMD JIT test (`test_clamp_position`) still passes **64/64** (no regression).

AMD CI validation on the per-commit runner arch (**mi325 / gfx942**), dispatched on the merged tip — both lanes green:

- [x] rocm700 · mi325 — `jit-kernel-unit-test-amd`: ✅ https://github.com/sgl-project/sglang/actions/runs/28542194827
- [x] rocm720 · mi325 — `jit-kernel-unit-test-amd-rocm720`: ✅ https://github.com/sgl-project/sglang/actions/runs/28542197164
- [x] NVIDIA `jit-kernel-unit-test` (+ multigpu / benchmark) green — kernel change is `kDLGPU`, identical to `kDLCUDA` on CUDA; `register_cuda_ci` lines untouched.

> Note: unrelated red checks on this PR (`base-b-test-*`, `build-test`, `npu`, `b200`, `multimodal-gen-*`) are pre-existing infra failures that are also red on `main`; they don't exercise the kernels touched here.

## Notes / follow-ups

Other JIT kernels remain AMD-blocked by *different*, per-kernel portability issues (out of scope here to keep this focused): raw CUDA includes (`cuda_runtime.h`, `cuda_bf16.h`), `cooperative_groups/reduce.h`, 32-bit warp-mask `__shfl_*_sync`/`__ballot_sync` (HIP requires 64-bit masks), inline manual `device_type == kDLCUDA` checks, and tests whose oracle is NVIDIA-only (`flashinfer`, `flash_attn`, `vllm`). These can be follow-up PRs.























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28573021527](https://github.com/sgl-project/sglang/actions/runs/28573021527)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28573021433](https://github.com/sgl-project/sglang/actions/runs/28573021433)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
