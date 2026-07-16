---
source_id: sglang-github-closed-issues-prs
title: '[DSA] Guard move_kv_cache against page-indexed corruption for page_size>1'
canonical_url: https://github.com/sgl-project/sglang/pull/31215
captured_at: '2026-07-14T23:40:21.667553+00:00'
content_hash: d4cfe59d8b0785d23fc8206bef610a8304be9523e904028d13833d4db36c5e5b
---
# [DSA] Guard move_kv_cache against page-indexed corruption for page_size>1

URL: https://github.com/sgl-project/sglang/pull/31215
State: closed
Labels: 
Closed at: 2026-07-14T17:59:43Z
Merged at: 

## Problem
`DSATokenToKVPool.move_kv_cache` (`srt/mem_cache/memory_pool.py`) moves the DSA indexer cache with:

```python
for index_k in self.index_k_with_scale_buffer:   # PAGE-indexed: (num_pages, page_size*(...))
    index_k[tgt_loc_flat] = index_k[src_loc_flat]  # tgt/src are per-TOKEN locations
```

`index_k_with_scale_buffer` is **page-indexed** (dim-0 is `num_pages`, with `page_size` tokens packed along
dim-1), but `tgt_loc/src_loc` are **token** locations. This is correct only for `page_size == 1`; for
`page_size == 64` (all CUDA DSA) it indexes the page dimension with token indices → wrong rows / OOB → silent
indexer-cache corruption. It is reached only via `move_accept_tokens_to_target_kvcache` on the **topk>1
tree-draft** path (`srt/speculative/spec_utils.py`); the topk==1 chain (e.g. GLM-5.2) never hits it, so it is
latent today.

## Fix
Add a fail-fast guard at the top of the method: for `page_size != 1`, raise `NotImplementedError` (before any
move, preserving the method's all-or-nothing contract) explaining that a page-aware move is required before
tree-drafting (topk>1) is enabled on DSA. The `page_size == 1` path and the base MLA `super().move_kv_cache`
(token-indexed, correct) are unchanged. A page-aware rewrite is deliberately out of scope — this stops silent
corruption cheaply until tree-drafting on DSA is actually wired up.

## Testing (all pass)

**`test/registered/unit/mem_cache/test_dsa_move_kv_cache_guard.py`** — GPU-free, **2/2 PASSED**:
| method | asserts |
|---|---|
| `test_move_kv_cache_raises_for_page_size_gt_1` | `page_size` ∈ {16, 64} raises `NotImplementedError` (fails on pre-fix code, which silently mis-moves); the 16 case pins `!= 1` vs a wrong `== 64` |
| `test_move_kv_cache_page_size_1_moves_without_guard` | `page_size == 1` does not raise and moves the correct row |







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29354807603](https://github.com/sgl-project/sglang/actions/runs/29354807603)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29354807313](https://github.com/sgl-project/sglang/actions/runs/29354807313)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
