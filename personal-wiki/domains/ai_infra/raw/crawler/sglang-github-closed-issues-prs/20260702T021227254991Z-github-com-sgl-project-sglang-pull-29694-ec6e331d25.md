---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Fix int8 per-token quant Triton portability + register test for AMD
  nightly CI'
canonical_url: https://github.com/sgl-project/sglang/pull/29694
captured_at: '2026-07-02T02:12:27.254991+00:00'
content_hash: ec6e331d25af792aea1359c9810a21938b3841052a268c92144e0d5c781306b7
---
# [AMD] Fix int8 per-token quant Triton portability + register test for AMD nightly CI

URL: https://github.com/sgl-project/sglang/pull/29694
State: closed
Labels: run-ci
Closed at: 2026-07-01T19:56:34Z
Merged at: 2026-07-01T19:56:34Z

## Summary

Two changes that together unblock the int8 fused-MoE kernel test on AMD (self-contained, independently mergeable):

1. **Portability fix** in `python/sglang/srt/layers/quantization/int8_kernel.py`: `_per_token_quant_int8` called `tl.extra.cuda.libdevice.round`, a CUDA-only Triton intrinsic. AMD's Triton backend rejects it at compile time:
   ```
   RuntimeError: Implicit conversion of CUDA __nv_roundf device function has been dropped;
   please update your source program to use triton.language.extra.<op> to replace triton.language.extra.cuda.<op>
   ```
   The CUDA path is kept **byte-for-byte unchanged** (`tl.extra.cuda.libdevice.round`); only on ROCm/HIP do we use the backend-agnostic `from triton.language.extra import libdevice` / `libdevice.round(...)` (the same portable pattern already used in `layers/triton_ops/softcap.py`). The two are selected by an `IS_HIP: tl.constexpr` branch, so Triton prunes the dead branch at compile time and the CUDA-only intrinsic is never lowered on AMD.

   ```python
   if IS_HIP:
       x_q = libdevice.round(x_q).to(tl.int8)          # ROCm: portable libdevice
   else:
       x_q = tl.extra.cuda.libdevice.round(x_q).to(tl.int8)  # CUDA: unchanged
   ```

2. **Register** `quant/test_int8_kernel.py` to the `nightly-amd-kernel-1-gpu` suite (additive `register_amd_ci`, keeps the existing `register_cuda_ci`).

## Root cause (runtime-confirmed)

The kernel compiled on CUDA but failed at Triton compile on ROCm (gfx950) because `tl.extra.cuda.libdevice.round` maps to the CUDA `__nv_roundf` device function, which the AMD backend dropped. The reference path in the test (`per_token_quant_int8`) hit this first, so every parametrization errored before reaching the correctness assertion.

## Verified on real MI35x (gfx950, per-file `pytest`)

`PYTHONPATH` set to the checkout (shadowing the image), `SGLANG_USE_AITER=1`, on both stacks:

| Test | ROCm 7.0 | ROCm 7.2 |
| --- | --- | --- |
| `quant/test_int8_kernel` (1 test / 32 subtests) | ✅ 1 passed | ✅ 1 passed + 32 subtests |

Numerics match the torch reference within ~3e-3 relative error (threshold 0.05). Before the fix: 32 failed (Triton compile error).

## ✅ Dispatched CI verification (`run_suite` nightly kernel job)

`run_suite.py --hw amd --suite nightly-amd-kernel-1-gpu --nightly`, both `nightly-test-1-gpu-kernel` jobs run `test_int8_kernel` green (`passed: true`, ~29s, not skipped):
- ROCm 7.0 — [Run #28411605827](https://github.com/sgl-project/sglang/actions/runs/28411605827)
- ROCm 7.2 — [Run #28411606573](https://github.com/sgl-project/sglang/actions/runs/28411606573)

## Approach / scope

- Minimal, targeted: one import + a HIP-guarded call-site change in the kernel; one additive registration line in the test. **CUDA path unchanged** (guarded by `IS_HIP` constexpr); NV / MUSA jobs untouched, CUDA registration preserved.
- `nightly-amd-kernel-1-gpu` is already wired in `nightly-test-amd.yml` / `nightly-test-amd-rocm720.yml`, so no workflow changes are needed.
- `collect_tests(sanity_check=True)` + `validate_all_suites` pass; the test is collected into `nightly-amd-kernel-1-gpu`. The file has a `__main__` entry.

## Test plan

- [x] AMD nightly `nightly-amd-kernel-1-gpu` runs the test on ROCm 7.0 and 7.2 (green on both — see runtime table and dispatched CI runs above).
- [x] No change to CUDA behavior (`IS_HIP` constexpr prunes the AMD branch on CUDA; CUDA registration untouched).





















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28412208681](https://github.com/sgl-project/sglang/actions/runs/28412208681)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28488652903](https://github.com/sgl-project/sglang/actions/runs/28488652903)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
