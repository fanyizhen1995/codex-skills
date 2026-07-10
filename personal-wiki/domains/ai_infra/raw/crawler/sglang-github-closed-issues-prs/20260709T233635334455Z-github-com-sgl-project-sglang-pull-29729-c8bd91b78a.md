---
source_id: sglang-github-closed-issues-prs
title: Add opt-in SGLANG_ROPE_CACHE_FP32 to keep RoPE cache in fp32 on non-CUDA
canonical_url: https://github.com/sgl-project/sglang/pull/29729
captured_at: '2026-07-09T23:36:35.334455+00:00'
content_hash: c8bd91b78a161565f793c1b356b9db2a4099e5ff95638338d1eecb3b193ce0e7
---
# Add opt-in SGLANG_ROPE_CACHE_FP32 to keep RoPE cache in fp32 on non-CUDA

URL: https://github.com/sgl-project/sglang/pull/29729
State: closed
Labels: run-ci
Closed at: 2026-07-09T09:10:39Z
Merged at: 2026-07-09T09:10:39Z

## Motivation

The RoPE cos/sin cache is kept in fp32 only on CUDA; every other backend
downcasts it to the model dtype:

```python
# NOTE(ByronHsu): cache needs to be in FP32 for numerical stability
if not _is_cuda:
    cache = cache.to(dtype)
```

On non-CUDA backends (observed on ROCm) this loses precision relative to the
CUDA path and introduces measurable RoPE numerical drift versus the reference.

## Modifications

- Add an opt-in `SGLANG_ROPE_CACHE_FP32` env var (`EnvBool(False)`, grouped
  under the existing RoPE cache configuration block in `environ.py`).
- When set, non-CUDA backends keep the cos/sin cache in fp32, matching the
  CUDA precision. Default behavior is unchanged.
- Hoist the `envs` import in `rotary_embedding/base.py` to module scope.

## Checklist

- [x] Default behavior unchanged (opt-in flag, default off).
- [x] Formatted with isort/black per repo config.



















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28986087036](https://github.com/sgl-project/sglang/actions/runs/28986087036)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28986086944](https://github.com/sgl-project/sglang/actions/runs/28986086944)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
