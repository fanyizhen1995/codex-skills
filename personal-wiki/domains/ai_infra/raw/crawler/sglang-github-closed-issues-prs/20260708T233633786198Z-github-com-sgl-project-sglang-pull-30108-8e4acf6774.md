---
source_id: sglang-github-closed-issues-prs
title: '[Fix] Torch-allocate dsv4 compress-plan out-params for stream-ordered lifetime'
canonical_url: https://github.com/sgl-project/sglang/pull/30108
captured_at: '2026-07-08T23:36:33.786198+00:00'
content_hash: 8e4acf6774b732a00e773e03d357502ce7f7b8655c953504a7d9122bc02d7a1f
---
# [Fix] Torch-allocate dsv4 compress-plan out-params for stream-ordered lifetime

URL: https://github.com/sgl-project/sglang/pull/30108
State: closed
Labels: jit-kernel
Closed at: 2026-07-08T03:00:46Z
Merged at: 

The dsv4 compress-plan builders (`plan_compress_prefill` / `plan_compress_decode` and their legacy variants) allocate their plan tensors internally via `ffi::empty` and return them through DLPack. That gives the tensors a non-stream-ordered lifetime: once the Python ref drops, the caching allocator can recycle the memory while a downstream store/rope kernel enqueued during CUDA-graph capture is still reading it — a use-after-recycle that can surface as a wild store / illegal memory access during capture.

Fix: allocate the plan out-params with torch (stream-ordered lifetime) in Python and pass them in, mirroring the existing online-compress path which already does exactly this. The C++ builders fill the caller's buffers and return the `(num_c, num_w)` counts (prefill) / void (decode). No happy-path behavior change.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28701606329](https://github.com/sgl-project/sglang/actions/runs/28701606329)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28701606257](https://github.com/sgl-project/sglang/actions/runs/28701606257)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
