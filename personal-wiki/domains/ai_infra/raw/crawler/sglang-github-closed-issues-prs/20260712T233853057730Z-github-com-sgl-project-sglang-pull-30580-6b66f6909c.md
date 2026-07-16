---
source_id: sglang-github-closed-issues-prs
title: Lazy load TileLang MHC kernels
canonical_url: https://github.com/sgl-project/sglang/pull/30580
captured_at: '2026-07-12T23:38:53.057730+00:00'
content_hash: 6b66f6909ca7a55ca153878fefeacdd56ae50142095aa0cc56d353d837a99708
---
# Lazy load TileLang MHC kernels

URL: https://github.com/sgl-project/sglang/pull/30580
State: closed
Labels: deepseek, run-ci
Closed at: 2026-07-12T00:32:28Z
Merged at: 2026-07-12T00:32:28Z

## Summary

This keeps TileLang out of the DeepSeek V4 import path until we actually need it. Model-registry discovery imports a lot of model files, so it should not also load TileLang's native CUDA stubs just because one unrelated module was discovered.

`deepseek_v4_rope.py` only uses Triton kernels, so it no longer imports TileLang at module load. `mhc.py` uses a small lazy proxy, which lets the existing `@tilelang.jit(...)` definitions stay in place while delaying the real TileLang import until the first MHC TileLang kernel call. The split-k MHC path loads TileLang before using `T.dynamic(...)` / `T.Tensor[...]`, and first-load / first-compile paths are guarded with locks.

















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29010339282](https://github.com/sgl-project/sglang/actions/runs/29010339282)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29010339047](https://github.com/sgl-project/sglang/actions/runs/29010339047)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
