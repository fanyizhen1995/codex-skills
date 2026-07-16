---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Remove ROCm page_first+kernel -> layer_first HiCache fallback (follow-up
  to #28534)'
canonical_url: https://github.com/sgl-project/sglang/pull/30622
captured_at: '2026-07-15T23:40:28.378881+00:00'
content_hash: b274c7d7cd86e495e2b847dafb51ee8b75a59980472b414c0a89107776dc7246
---
# [AMD] Remove ROCm page_first+kernel -> layer_first HiCache fallback (follow-up to #28534)

URL: https://github.com/sgl-project/sglang/pull/30622
State: closed
Labels: run-ci
Closed at: 2026-07-15T05:48:16Z
Merged at: 2026-07-15T05:48:16Z

## Motivation

#28534 enabled the JIT staged HiCache write-back path on ROCm:
- `can_use_jit` / `can_use_write_back_jit` are now allowed on HIP (not only CUDA) in the MHA/MLA host pools;
- `hicache.cuh` / `staged_write_back.cuh` build and run with hipcc (PTX-only helpers guarded by `USE_ROCM`, ROCm device-type matchers, vectorized non-temporal load/store).

As called out in #28534's description, once that landed, the ROCm `layer_first` fallback added by #28473 in `ServerArgs._resolve_layout_io_compatibility()` should be reverted.

## What this PR does

Removes the ROCm-only block that rewrites `page_first` + `kernel` to `layer_first`:

```python
# The page_first kernel write-back relies on the CUDA-only JIT staged
# kernel. On ROCm it falls back to a kernel that requires CUDA index
# tensors and crashes on host write-back, so use layer_first there.
if (
    self.hicache_mem_layout == "page_first"
    and self.hicache_io_backend == "kernel"
    and is_hip()
):
    self.hicache_mem_layout = "layer_first"
    logger.warning(...)
```

## Why it must be removed (not just cleanup)

The block runs at `ServerArgs` resolution time, i.e. **before** the host KV pool is created. On ROCm it forces any `page_first` + `kernel` request to `layer_first`, so ROCm can never reach the `page_first` + `kernel` JIT staged write-back path that #28534 just made correct. The two are directly contradictory: #28534 says "ROCm can use the JIT staged write-back", while this fallback says "ROCm always downgrades to layer_first". Leaving it in makes #28534's ROCm work dead code.

After this change, ROCm exercises the same `page_first` + `kernel` write-back path as CUDA (platform parity, retained staged write-back bandwidth), which is what #28534 validated on MI355X (gfx950, ROCm 7.2).

## Test plan

- [x] `is_hip` import still used elsewhere in `server_args.py` (no dead import); file byte-compiles.
- [x] HiCache JIT unit tests (`test/registered/jit/test_hicache.py`, `test_hicache_page_first_write_back.py`) pass on MI355X (ROCm 7.2) with the `page_first` + `kernel` JIT staged write-back path enabled (validated for #28534).
- [ ] CI: AMD `jit-kernel-unit` + HiCache serving suites.
- [ ] Optional: end-to-end `--enable-hierarchical-cache --hicache-mem-layout page_first --hicache-io-backend kernel` launch on ROCm no longer silently downgrades to `layer_first`.

























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29231811696](https://github.com/sgl-project/sglang/actions/runs/29231811696)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29231811508](https://github.com/sgl-project/sglang/actions/runs/29231811508)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
