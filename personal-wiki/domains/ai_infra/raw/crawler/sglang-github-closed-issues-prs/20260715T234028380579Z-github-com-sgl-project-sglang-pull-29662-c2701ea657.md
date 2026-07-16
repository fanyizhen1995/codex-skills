---
source_id: sglang-github-closed-issues-prs
title: Fix SWA pool exhaustion in decode _pre_alloc by passing swa_num_tokens
canonical_url: https://github.com/sgl-project/sglang/pull/29662
captured_at: '2026-07-15T23:40:28.380579+00:00'
content_hash: c2701ea6577bca2ca4b5ead1a3cea41719050b5ac1f753dace256b45d7907053
---
# Fix SWA pool exhaustion in decode _pre_alloc by passing swa_num_tokens

URL: https://github.com/sgl-project/sglang/pull/29662
State: closed
Labels: 
Closed at: 2026-07-15T04:22:23Z
Merged at: 

## Motivation

Under hybrid SWA models (e.g. DeepSeek-V4-Flash-Base) running PD-disaggregated
decode with `--disaggregation-decode-enable-radix-cache` +
`SGLANG_ENABLE_UNIFIED_RADIX_TREE=1`, the decode-side `_pre_alloc` path
crashes mid-run with `AssertionError: KV cache is full!` even though
`swa_evictable` is hundreds of thousands.

`SWATokenToKVPoolAllocator.available_size() = min(full, swa)`; when SWA is
the bottleneck, calling `evict(EvictParams(num_tokens=N))` only drives
`FullComponent.drive_eviction`, which walks `evictable_device_leaves` and
calls `_evict_device_leaf` on each — that frees the SWA chunk owned by the
evicted leaf (leaf-level eviction priorities are equal so all components on
the leaf are dropped), but ancestor nodes' SWA chunks (the SWA path data
covering the sliding window of other reqs) live on the SWA LRU as
tombstones and are only freed by `SWAComponent.drive_eviction`, which is
gated on `params.swa_num_tokens`. Without setting that field, those
internal SWA tombstones stay in place and `swa_available` remains below
`required_alloc_tokens`.

Diag captured before the assert (`swa_evicted=4352` came entirely from
leaves dropped by `_evict_device_leaf`; the 445K-slot internal SWA
tombstone backlog was never visited):

```
pre-evict  required=39168  num_to_evict=5120
  full_available=4368128  swa_available=34048
  full_evictable=435200   swa_evictable=449792
post-evict full_evicted=5120  swa_evicted=4352   (from leaves only)
  full_available=4373248  swa_available=38400 < 39168 → assert
```

## Changes

In `_pre_alloc`, when the allocator is `SWATokenToKVPoolAllocator`, compute
`num_tokens` / `swa_num_tokens` independently against each sub-pool's
`available_size` and pass both to `EvictParams`. 

























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: **Missing `run-ci` label** -- add it to run CI tests.<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: **Blocked** -- `run-ci` is required first.<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
