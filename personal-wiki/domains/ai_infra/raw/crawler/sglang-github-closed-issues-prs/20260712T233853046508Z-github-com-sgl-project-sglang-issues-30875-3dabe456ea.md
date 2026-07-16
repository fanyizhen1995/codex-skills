---
source_id: sglang-github-closed-issues-prs
title: '[Bug] FlashInfer allreduce fusion fails after flashinfer 0.6.14 upgrade: tilelang
  libcudart_stub.so picked up instead of real libcudart'
canonical_url: https://github.com/sgl-project/sglang/issues/30875
captured_at: '2026-07-12T23:38:53.046508+00:00'
content_hash: 3dabe456ea12835f6eaf6f54616e9c16cdc2253be85194c959ca80d487db396c
---
# [Bug] FlashInfer allreduce fusion fails after flashinfer 0.6.14 upgrade: tilelang libcudart_stub.so picked up instead of real libcudart

URL: https://github.com/sgl-project/sglang/issues/30875
State: closed
Labels: 
Closed at: 2026-07-12T03:53:08Z
Merged at: 

## Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

## Describe the bug

After the flashinfer 0.6.14 upgrade (sglang commit [`2c6cd1ef41`](https://github.com/sgl-project/sglang/commit/2c6cd1ef41c52713f78a0c5eb1333a197577c870), PR [#29910](https://github.com/sgl-project/sglang/pull/29910)), FlashInfer allreduce fusion workspace initialization fails on all TP ranks with:

```
Failed to initialize FlashInfer workspace (backend=trtllm): /usr/local/lib/python3.10/dist-packages/tilelang/lib/libcudart_stub.so: undefined symbol: cudaDeviceReset. Disabling flashinfer allreduce fusion permanently.
```

This disables flashinfer allreduce fusion permanently for the entire run.

## Root Cause

The upstream flashinfer PR [flashinfer-ai/flashinfer#3562](https://github.com/flashinfer-ai/flashinfer/pull/3562) changed `flashinfer/comm/cuda_ipc.py` from eagerly constructing `CudaRTLibrary` at import time to lazily constructing it on first use:

```python
# Before (eager — runs at import time when only real libcudart is loaded):
cudart = CudaRTLibrary()

# After (lazy — runs on first use, by which time tilelang is loaded):
class _LazyCudaRTLibrary:
    _library: Optional[CudaRTLibrary] = None

    def _get_library(self) -> CudaRTLibrary:
        if self._library is None:
            self._library = CudaRTLibrary()
        return self._library

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_library(), name)

cudart = _LazyCudaRTLibrary()
```

`CudaRTLibrary.__init__()` calls `find_loaded_library("libcudart")` which scans `/proc/self/maps` for any line containing the substring `"libcudart"`. With the eager approach, this ran at import time before tilelang was loaded, so it found the real `libcudart.so` from CUDA. With the lazy approach, by the time the first `cudart` method is called (during `create_allreduce_fusion_workspace`), **tilelang has already been imported** and its `libcudart_stub.so` is mapped into the process address space.

The naive substring match hits:
```
/usr/local/lib/python3.10/dist-packages/tilelang/lib/libcudart_stub.so
```

This stub `.so` is a link-time stub for compiling device code — it does not export all real cudart symbols (specifically `cudaDeviceReset` is missing). When flashinfer's `CudaRTLibrary` tries to resolve this symbol via `ctypes.CDLL`, it fails.

## Relevant References

| What | Link |
|------|------|
| SGLang commit that introduced the issue | [`2c6cd1ef41`](https://github.com/sgl-project/sglang/commit/2c6cd1ef41c52713f78a0c5eb1333a197577c870) — `[Dep] Upgrade flashinfer to 0.6.14 (#29910)` |
| SGLang PR | [#29910](https://github.com/sgl-project/sglang/pull/29910) |
| Upstream flashinfer PR that introduced lazy CudaRTLibrary | [flashinfer-ai/flashinfer#3562](https://github.com/flashinfer-ai/flashinfer/pull/3562) |
| FlashInfer `find_loaded_library` / `CudaRTLibrary` | `flashinfer/comm/cuda_ipc.py` lines 43–68, 70–139 |
| tilelang stub library | `/usr/local/lib/python3.10/dist-packages/tilelang/lib/libcudart_stub.so` |
| SGLang code that catches the exception | `python/sglang/srt/layers/flashinfer_comm_fusion.py` line 522–529 |

## Possible Fixes

1. **Fix in flashinfer** (preferred): Make `find_loaded_library` more specific — match `libcudart.so` or `libcudart-*.so` but exclude paths containing `_stub` or `stub`. E.g.:
   ```python
   if lib_name in line and "stub" not in line:
   ```
2. **Fix in tilelang**: Rename `libcudart_stub.so` to something that doesn't contain the `libcudart` substring (e.g., `libtilelang_cudart_stub.so`).
3. **Workaround in sglang**: Force an early import of `flashinfer.comm.cuda_ipc` (triggering `CudaRTLibrary` construction before tilelang loads), or pin a `find_loaded_library` override that filters out stub libraries.

## Reproduction

Run any multi-GPU inference with `--flashinfer-allreduce-fusion-backend trtllm` (or `auto` on SM90+) after the 0.6.14 upgrade, in an environment where `tilelang` is also installed (which is the case in sglang's standard dependencies since `tilelang==0.1.11` is in `pyproject.toml`):

```bash
python -m sglang.launch_server \
  --model-path <any-model> \
  --tp 8 \
  --flashinfer-allreduce-fusion-backend auto
```

All TP ranks will log:
```
[2026-07-09 21:37:15 TP0] Failed to initialize FlashInfer workspace (backend=trtllm): /usr/local/lib/python3.10/dist-packages/tilelang/lib/libcudart_stub.so: undefined symbol: cudaDeviceReset. Disabling flashinfer allreduce fusion permanently.
```

## Environment

- SGLang: latest main (post-commit `2c6cd1ef41`)
- flashinfer: 0.6.14
- tilelang: 0.1.11
- CUDA: 12.x
- Python: 3.10/3.12
- GPUs: 8x (TP=8, SM90+)
- OS: Linux
