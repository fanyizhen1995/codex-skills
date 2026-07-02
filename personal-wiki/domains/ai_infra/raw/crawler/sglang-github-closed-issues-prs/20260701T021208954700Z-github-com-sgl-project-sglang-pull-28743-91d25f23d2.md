---
source_id: sglang-github-closed-issues-prs
title: 'fix(dsa): guard cuda_runtime.h include so fused_metadata_copy builds on ROCm'
canonical_url: https://github.com/sgl-project/sglang/pull/28743
captured_at: '2026-07-01T02:12:08.954700+00:00'
content_hash: 91d25f23d2e9a497c6b3e89bebb50299a947ac86c3def7735869d19e166f0be5
---
# fix(dsa): guard cuda_runtime.h include so fused_metadata_copy builds on ROCm

URL: https://github.com/sgl-project/sglang/pull/28743
State: closed
Labels: jit-kernel
Closed at: 2026-06-30T21:22:39Z
Merged at: 

## Summary

The DSA fused metadata-copy JIT kernel (`python/sglang/jit_kernel/csrc/elementwise/fused_metadata_copy.cuh`) includes `<cuda_runtime.h>` unconditionally. The tvm-ffi JIT path compiles the `.cuh` directly with `hipcc -x hip` **without a hipify pass**, so on ROCm there is no `cuda_runtime.h` on the include path and compilation fails:

```
fused_metadata_copy.cuh:38:10: fatal error: 'cuda_runtime.h' file not found
   38 | #include <cuda_runtime.h>
```

This kernel is reached on AMD whenever `speculative_num_steps > 3`, which selects the **multi-backend** fused-copy path in `dsa_backend.py`. The single-backend path is already HIP-guarded (`_USE_FUSED_METADATA_COPY = ... and not _is_hip`), but the multi path is not. And because `cache_once` (`jit_kernel/utils.py`) only memoizes *successful* compiles, the failed build is retried on **every CUDA-graph replay** — the call site catches the error and falls back to the per-backend loop, but pays a full failed `hipcc` invocation per decode step, collapsing throughput to ~0.13 tok/s on gfx950.

The fix guards just the include with `#ifndef USE_ROCM`. The rest of the file is already HIP-compatible: `__grid_constant__` is shimmed in `include/sgl_kernel/utils.cuh`, and `host::LaunchKernel` has a `hipLaunchKernelGGL` branch.

## Test plan

Verified on MI350X (gfx950) / ROCm 7.2.4:

- [x] Before: `_jit_fused_metadata_copy_multi_module(...)` fails with the `cuda_runtime.h` fatal error above.
- [x] After: the multi kernel compiles cleanly (no further HIP errors) for `has_real_page_table` ∈ {false, true} and `has_flashmla` ∈ {false, true}.
- [x] Functional test: launched the compiled kernel on synthetic `int32` tensors and compared against a torch reference — `cache_seqlens`, `cu_seqlens_k[1:]`, page table (`col < max_len`), `dsa_cache_seqlens`, `dsa_cu_seqlens_k[1:]`, and `real_page_table` all copy exactly to all three destination backends; index-0 and the page-table tail are correctly left untouched. PASS for both `has_real_page_table` false and true.

Note: this restores `num_steps > 3` *throughput* on ROCm; it is independent of the gfx950 block-FP8 accuracy issue tracked in #28685.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #27849498701](https://github.com/sgl-project/sglang/actions/runs/27849498701)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27849498600](https://github.com/sgl-project/sglang/actions/runs/27849498600)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
