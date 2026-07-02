---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Register ltx2_ada_values JIT kernel test for AMD nightly CI'
canonical_url: https://github.com/sgl-project/sglang/pull/29693
captured_at: '2026-07-02T02:12:27.256665+00:00'
content_hash: d9143e4f9953073512b57c96056b65b64cf956671dddd82c1654013a8de8f1c8
---
# [AMD] Register ltx2_ada_values JIT kernel test for AMD nightly CI

URL: https://github.com/sgl-project/sglang/pull/29693
State: closed
Labels: 
Closed at: 2026-07-01T08:13:56Z
Merged at: 2026-07-01T08:13:56Z

## Summary

Adds an AMD nightly registration for the `ltx2_ada_values` JIT kernel unit test, which currently runs only on NVIDIA.

- `test/registered/jit/diffusion/test_ltx2_ada_values.py`: add `register_amd_ci(est_time=8, suite="nightly-amd-kernel-1-gpu", nightly=True)`.

## Why this kernel is ROCm-portable

- `ltx2_ada_values9` is a pure **Triton** kernel (`python/sglang/jit_kernel/diffusion/triton/ltx2_ada_values.py`), so it compiles and runs on ROCm via Triton's HIP backend — no CUDA C++ sources to hipify.
- The test's reference oracle is pure torch (broadcast add + `unbind`) compared at `atol=0, rtol=0`; the kernel is a simple elementwise add, so results are bit-exact on ROCm. No `flashinfer` / `sgl_kernel` dependency.
- Same class as the Triton diffusion kernels already AMD-registered in this suite (`test_varlen_pack_pad`, `test_group_norm_silu`, `test_qwen_image_modulation`, `test_flydsl_fused_norm`).

## Approach

Purely additive and AMD-only. The existing `register_cuda_ci(...)` is unchanged; one `register_amd_ci(..., nightly=True)` line is added. The `nightly-amd-kernel-1-gpu` suite is already wired into `nightly-test-amd.yml` and `nightly-test-amd-rocm720.yml`, so no workflow changes are needed.

## Validation

Dispatched the `nightly-amd-kernel-1-gpu` suite against this branch on real MI3xx hardware — green on **both** ROCm stacks:

- **ROCm 7.0**: ✅ PASSED — https://github.com/sgl-project/sglang/actions/runs/28411145991 — `test_ltx2_ada_values.py`: `{"passed": true, "elapsed": 9}` (all variants + shape-rejection check).
- **ROCm 7.2**: ✅ PASSED — https://github.com/sgl-project/sglang/actions/runs/28411146732 — `test_ltx2_ada_values.py`: `{"passed": true, "elapsed": 6}`.

## Test plan

- [x] AMD nightly kernel CI (ROCm 7.0) passes on MI3xx — `test_ltx2_ada_values` green.
- [x] AMD nightly kernel CI (ROCm 7.2) passes on MI3xx — `test_ltx2_ada_values` green.
- [x] NVIDIA registration unchanged (no behavior change on CUDA).







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28483795921](https://github.com/sgl-project/sglang/actions/runs/28483795921)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28483795809](https://github.com/sgl-project/sglang/actions/runs/28483795809)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
