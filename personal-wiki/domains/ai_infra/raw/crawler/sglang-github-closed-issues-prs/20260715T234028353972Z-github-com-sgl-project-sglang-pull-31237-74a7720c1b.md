---
source_id: sglang-github-closed-issues-prs
title: '[not to merge] fix: fall back to no_buffer mamba radix cache on ROCm (no FLA)'
canonical_url: https://github.com/sgl-project/sglang/pull/31237
captured_at: '2026-07-15T23:40:28.353972+00:00'
content_hash: 74a7720c1b8ec6e1633474229db5bceb7c5d7759f88b6e6b59979878ea0c2f0a
---
# [not to merge] fix: fall back to no_buffer mamba radix cache on ROCm (no FLA)

URL: https://github.com/sgl-project/sglang/pull/31237
State: closed
Labels: run-ci
Closed at: 2026-07-15T20:06:50Z
Merged at: 

## Motivation

`test_qwen35_eval_mi35x.py` (job `nightly-8-gpu-mi35x-qwen35`, and the mi30x `nightly-8-gpu-qwen35`) fails on **AMD gfx950 (MI35x) / ROCm**: the server exits at startup with

```
AssertionError: extra_buffer needs CUDA/MUSA/NPU (FLA).
```

### Root cause

The `mamba_radix_cache_strategy="auto"` resolution (now in `arg_groups/overrides.py::_mamba_radix_cache_resolution`) picks **`extra_buffer`** whenever the model supports it (hybrid mamba models such as Qwen3.5 with `linear_attn_backend="triton"`) and radix cache with overlap/paging is enabled. But `extra_buffer` requires the FLA backend, guarded by `assert is_cuda() or is_musa() or is_npu()` in `ServerArgs._validate_mamba_extra_buffer`, so on ROCm/HIP the server crashes during `ServerArgs` init — before any weights are loaded.

This regressed in #28151 ("refactor: mamba radix cache server args initialize", merged 2026-06-18, `66a7fd5c0b`), which removed the previous unconditional `auto -> no_buffer` fallback. The last green `nightly-8-gpu-mi35x-qwen35` run was 2026-06-15.

This supersedes the now-stale #29965 (same class of fix, but the resolution logic has since moved out of `server_args.py` into `arg_groups/overrides.py`).

## Modifications

Scope the change to **AMD/HIP only**: in the `auto` path, when running on ROCm (`is_hip()`), fall back to `no_buffer` (which disables the overlap scheduler, as it already requires) instead of selecting `extra_buffer`. On every other platform (CUDA/MUSA/NPU/etc.) the resolution is byte-for-byte unchanged.

## Verification

- ROCm/HIP: `auto` now resolves to `no_buffer`, `MambaRadixCache` initializes and the server serves (previously aborted at init).
- CUDA/MUSA/NPU: `not is_hip()` is `True`, so selection is unchanged.

## Checklist

- [x] Format code with pre-commit.
- [ ] Add unit tests.
- [ ] Update documentation as needed.















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29377857034](https://github.com/sgl-project/sglang/actions/runs/29377857034)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29377920040](https://github.com/sgl-project/sglang/actions/runs/29377920040)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
