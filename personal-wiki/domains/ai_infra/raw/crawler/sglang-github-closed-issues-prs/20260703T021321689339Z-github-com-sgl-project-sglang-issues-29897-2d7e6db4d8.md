---
source_id: sglang-github-closed-issues-prs
title: '[Bug] dsv3_fused_a_gemm crashes on SM120: pipeline sized against a hardcoded
  192KB smem budget (193KB request vs 99KB limit), cudaFuncSetAttribute failure unchecked'
canonical_url: https://github.com/sgl-project/sglang/issues/29897
captured_at: '2026-07-03T02:13:21.689339+00:00'
content_hash: 2d7e6db4d834625eb224f8d5f2bbdaf56fe68f9382c0089e30db2b5986724098
---
# [Bug] dsv3_fused_a_gemm crashes on SM120: pipeline sized against a hardcoded 192KB smem budget (193KB request vs 99KB limit), cudaFuncSetAttribute failure unchecked

URL: https://github.com/sgl-project/sglang/issues/29897
State: closed
Labels: 
Closed at: 2026-07-03T00:12:46Z
Merged at: 

### Describe the bug

`dsv3_fused_a_gemm` crashes on SM120 (RTX PRO 6000 / RTX 5090 class) with

```
torch.AcceleratorError: CUDA error: invalid argument
```

All 4 cases of `sgl-kernel/tests/test_dsv3_fused_a_gemm.py` fail this way on an RTX PRO 6000 (CUDA 13, torch 2.11 cu130, sgl-kernel 0.4.4).

### Root cause

`invokeFusedAGemm` (sgl-kernel/csrc/gemm/dsv3_fused_a_gemm.cu) sizes its software pipeline against a hardcoded 192 KB shared-memory budget:

```cpp
constexpr int max_stage_cnt = 1024 * 192 / ((tile_m + tile_n) * tile_k * sizeof(bf16_t));
...
constexpr int smem_bytes = ((tile_m * 2 + tile_n * 2) * tile_k * stage_cnt + barrier_bytes + 1023) / 1024 * 1024;
```

For both shipped instantiations (`kTileN = 8`: stage_cnt 16, and `kTileN = 16`: stage_cnt 12) this evaluates to `smem_bytes = 197632` (193 KB). That fits Hopper's 227 KB opt-in limit, but SM120's `cudaDevAttrMaxSharedMemoryPerBlockOptin` is 101376 bytes (99 KB), so:

1. `cudaFuncSetAttribute(..., cudaFuncAttributeMaxDynamicSharedMemorySize, 197632)` fails - and its return value is not checked, so the failure is silent;
2. `cudaLaunchKernelEx` with `dynamicSmemBytes = 197632` then fails with `cudaErrorInvalidValue`.

### Expected fix shape

Parameterize the pipeline budget by the device's opt-in shared memory instead of hardcoding 192 KB: with a 96 KB budget the same formula gives stage_cnt 8 (`kTileN=8`) / 6 (`kTileN=16`) and `smem_bytes = 99328 <= 101376`, and the kernel already supports `stage_cnt < k_iter_cnt` (it runs stage_cnt 16 < k_iter 28 on Hopper today). Since `stage_cnt` is a template parameter, that means instantiating a second (smaller-budget) variant and dispatching on the device limit at runtime - plus checking the `cudaFuncSetAttribute` return so an unsupported configuration fails loudly. I have a fix along these lines working locally and will send a PR after verifying on the real card.

### Environment

RTX PRO 6000 Blackwell (SM120, sharedMemPerBlockOptin=101376), CUDA 13.0, torch 2.11.0+cu130, sgl-kernel 0.4.4, sglang main `bac351d`. Found during a systematic SM120 sweep of the sgl-kernel test suite.
