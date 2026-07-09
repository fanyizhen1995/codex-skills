---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Register 3 ROCm-portable JIT kernel tests for AMD CI'
canonical_url: https://github.com/sgl-project/sglang/pull/30212
captured_at: '2026-07-08T23:36:33.788658+00:00'
content_hash: 8e0f19233dbaab16f287fff211689bbb540050d24d2c8fc934360e9014bcf472
---
# [AMD] Register 3 ROCm-portable JIT kernel tests for AMD CI

URL: https://github.com/sgl-project/sglang/pull/30212
State: closed
Labels: run-ci
Closed at: 2026-07-08T20:38:18Z
Merged at: 2026-07-08T20:38:17Z

## Summary
Moves the JIT kernel correctness tests that **actually compile and pass on ROCm** onto the registered `test/registered/jit/` path (the same mechanism NVIDIA uses via `register_cuda_ci`) by adding `register_amd_ci(suite="jit-kernel-unit-test-amd")`.

Registered tests:
- **`test_rmsnorm.py`** — on ROCm (`is_hip()`), `flashinfer_rmsnorm` uses a torch reference so the JIT rmsnorm is validated; the NVIDIA path is unchanged (flashinfer only).
- **`test_rope.py`** — implemented the previously-stubbed `torch_impl_rope` (NeoX + interleaved/GPT-J, partial-rope aware, matching the `[cos|sin]` cache layout); on ROCm (`is_hip()`) `flashinfer_rope` uses it, NVIDIA still uses flashinfer. Verified **bit-exact (0.0 error)** vs an independent complex-rotation reference; ROCm run reports 218 passed / 8 skipped.
- **`test_dsv32_indexer_fusion.py`** — has an `is_hip()` code path and passes on ROCm.

**NVIDIA behavior is unchanged**: the torch references are gated behind `is_hip()`, so on CUDA every test takes the original flashinfer path verbatim.

## Why only 3
This effort originally attempted ~22 JIT tests, but ROCm CI showed the large majority of these kernels are **CUDA-only at the source level** (`cuda_fp16.h` / `cuda_bf16.h` / `cuda_runtime.h` / `cub/cub.cuh` / `cooperative_groups.h` not found, `nv_bfloat16` types, CUDA inline-asm). Those cannot be registered for AMD until the kernels themselves are ported to HIP — not fixable from the test side. This PR registers exactly the ones that pass. (Supersedes #30213/#30219/#30220.)

## Test plan
Validated on **both** AMD ROCm CI lanes:
- [x] `scripts/ci/check_registered_tests.py` passes.
- [x] `collect_tests()` resolves all 3 to `suite=jit-kernel-unit-test-amd`.
- [x] `torch_impl_rope` matches an independent complex-rotation reference (NeoX + GPT-J), max err 0.0.
- [x] `jit-kernel-unit-test-amd` green on **ROCm 7.0** (`rocm700`) — run [28829593964](https://github.com/sgl-project/sglang/actions/runs/28829593964) ✅
- [x] `jit-kernel-unit-test-amd-rocm720` green on **ROCm 7.2** (`rocm720`) — run [28829596371](https://github.com/sgl-project/sglang/actions/runs/28829596371) ✅







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28918003403](https://github.com/sgl-project/sglang/actions/runs/28918003403)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28918003333](https://github.com/sgl-project/sglang/actions/runs/28918003333)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
