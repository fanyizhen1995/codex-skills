---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Register fused_metadata_copy JIT kernel test for AMD nightly CI'
canonical_url: https://github.com/sgl-project/sglang/pull/29671
captured_at: '2026-07-01T02:12:08.966745+00:00'
content_hash: 9bb0ad54dc534f8196e55369511b6907fca42dc550e3af2b593507f2728d5335
---
# [AMD] Register fused_metadata_copy JIT kernel test for AMD nightly CI

URL: https://github.com/sgl-project/sglang/pull/29671
State: closed
Labels: run-ci
Closed at: 2026-06-30T04:26:12Z
Merged at: 2026-06-30T04:26:12Z

## Summary

Adds an AMD nightly registration for the `fused_metadata_copy` JIT kernel unit test, which currently runs only on NVIDIA.

- `test/registered/jit/test_fused_metadata_copy.py`: add `register_amd_ci(est_time=100, suite="nightly-amd-kernel-1-gpu", nightly=True)`.

## Why this kernel is ROCm-portable

- The kernel is a pure `int32` metadata copy/gather (`cache_seqlens`, `cu_seqlens_k`, `page_table`, DSA metadata, optional FlashMLA metadata) — no NVIDIA-only math.
- The JIT source `python/sglang/jit_kernel/csrc/elementwise/fused_metadata_copy.cuh` already carries an explicit ROCm path (`#ifndef USE_ROCM ... #else <hip/hip_runtime.h> ... #endif`), so it compiles under `hipcc` via the `load_jit` `-DUSE_ROCM` flow.
- The test's reference oracle is pure torch (`.copy_()` + `torch.equal`), with no `flashinfer` / `sgl_kernel`-only dependency, so it runs on ROCm without NVIDIA-only libraries.
- Same class as the existing AMD-registered copy kernels in this suite (`test_fused_store_index_cache`, `test_kvcacheio_asymmetric`).

## Approach

Purely additive and AMD-only. The existing `register_cuda_ci(...)` registrations are unchanged; one `register_amd_ci(..., nightly=True)` line is added. The `nightly-amd-kernel-1-gpu` suite is already wired into `nightly-test-amd.yml` and `nightly-test-amd-rocm720.yml` (`--timeout-per-file 900`, well above `est_time=100`), so no workflow changes are needed.

## Validation

Dispatched the `nightly-amd-kernel-1-gpu` suite (`nightly-test-1-gpu-kernel` job) against this branch on real MI3xx hardware — green on **both** ROCm stacks:

- **ROCm 7.0**: ✅ PASSED — https://github.com/sgl-project/sglang/actions/runs/28395147277 — `test_fused_metadata_copy.py`: 42 passed, `{"passed": true, "elapsed": 49}`.
- **ROCm 7.2**: ✅ PASSED — https://github.com/sgl-project/sglang/actions/runs/28395148836 — `test_fused_metadata_copy.py`: `{"passed": true, "elapsed": 52}`.

(All variants pass: single/multi-backend, large-batch, dtype validation. est_time=100, elapsed ~49–52s.)

## Test plan

- [x] AMD nightly kernel CI (ROCm 7.0) passes on MI3xx — `test_fused_metadata_copy` green.
- [x] AMD nightly kernel CI (ROCm 7.2) passes on MI3xx — `test_fused_metadata_copy` green.
- [x] NVIDIA registrations unchanged (no behavior change on CUDA).
