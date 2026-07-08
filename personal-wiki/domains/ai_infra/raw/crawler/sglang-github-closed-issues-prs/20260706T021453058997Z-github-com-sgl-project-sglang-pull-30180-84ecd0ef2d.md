---
source_id: sglang-github-closed-issues-prs
title: 'Cleanup: relocate temp_set_env and consolidate multi-device/CUDA helpers in
  common.py'
canonical_url: https://github.com/sgl-project/sglang/pull/30180
captured_at: '2026-07-06T02:14:53.058997+00:00'
content_hash: 84ecd0ef2d10c99b7fb01ad2510e2adc84f9fd951d89a2bfa8c27ac8fd512f81
---
# Cleanup: relocate temp_set_env and consolidate multi-device/CUDA helpers in common.py

URL: https://github.com/sgl-project/sglang/pull/30180
State: closed
Labels: Multi-modal, run-ci, bypass-fastfail
Closed at: 2026-07-06T01:47:27Z
Merged at: 2026-07-06T01:47:27Z

## Motivation

Two small, behavior-neutral cleanups to `python/sglang/srt/utils/common.py` and `python/sglang/srt/environ.py`:

1. **Move `temp_set_env` out of `environ.py`.** `temp_set_env` is a general-purpose env helper that explicitly *rejects* sglang-owned (`SGLANG_*`/`SGL_*`) keys, so it doesn't belong in `environ.py` (which is the home for sglang-owned env-var descriptors). It now lives in `utils/common.py` next to the sibling helpers `get_bool_env_var` / `get_int_env_var`. All callers updated.

2. **Consolidate all multi-device / CUDA-version helpers into one section** at the top of `common.py`, delimited by clear `BEGIN`/`END` banners plus guidance telling future developers to only add hardware/backend-detection, CUDA/HIP/driver-version, or device-capability/selection code there. Previously these ~70 helpers were scattered across the 4300-line file.

## What's in scope

- `is_cuda`/`is_hip`/`is_npu`/`is_xpu`/`is_hpu`/`is_cpu`/`is_musa`/`is_mps` + host-CPU arch detection
- SM/architecture capability (`is_sm*_supported`, `is_blackwell`, `is_ampere/hopper`, `_check_cuda_device_version`)
- CUDA/HIP/driver versions (`get_cuda_version`, `get_hip_version`, `get_nvidia_driver_version*`, `is_nvidia_cublas_version_ge_12_9`)
- Backend feature availability (AMX/XMX, FlashInfer, tokenspeed)
- Device module/selection/context, enumeration/info, and `get_*_memory_capacity` probes

## Guarantee: pure code motion, no behavior change

This is entirely relocation + import rewiring. Verified with an AST-level diff against `main` (using `ast.dump`, which ignores formatting/comments/line-numbers but captures all logic, docstrings, decorators, and nesting):

- **Zero changed function/class bodies** across all 6 files.
- Only def-level delta: `temp_set_env` moves from `environ.py` → `common.py` (byte-identical AST).
- `common.py` module-level statements (FP8 constants, `builtins` assigns, `is_sm*` assigns, `try` blocks): **preserved identically**.
- The moved section keeps blocks in original relative order, so intra-section load-time dependencies remain satisfied.
- Confirmed the module **actually imports** and the package `import *` re-exports still resolve.
- `pre-commit` (isort/ruff/black/...) passes.





































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28757902678](https://github.com/sgl-project/sglang/actions/runs/28757902678)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28758400459](https://github.com/sgl-project/sglang/actions/runs/28758400459)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
