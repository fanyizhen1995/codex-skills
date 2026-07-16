---
source_id: sglang-github-closed-issues-prs
title: '[style] Extract init-static values in memory-cache path'
canonical_url: https://github.com/sgl-project/sglang/pull/30710
captured_at: '2026-07-10T23:37:20.332298+00:00'
content_hash: db701bd52101646199facd221a69082718102aec38df96f925c5d425f2fb6c9b
---
# [style] Extract init-static values in memory-cache path

URL: https://github.com/sgl-project/sglang/pull/30710
State: closed
Labels: run-ci
Closed at: 2026-07-10T02:38:15Z
Merged at: 2026-07-10T02:38:15Z

Follows the new **"Extract init-static values at construction"** rule (#30701): when a derived value's inputs are frozen for the object's lifetime, compute it once in `__init__` and read the attribute instead of re-deriving in hot paths.

This PR covers the **memory-cache storage backends + KV pools** subsystem.

## Changes

**`eic_storage.py`**
- Cache `mha_zero_copy = use_zero_copy and not is_mla_model` in `__init__`; replaces 4 per-request reads (also fixes an inverted operand-order inconsistency at one site).

**`storage_hf3fs.py`**
- Compute `mha_zero_copy` in `register_mem_pool_host` (where `is_zero_copy` gets its final value; `is_mla_model` is already frozen from `__init__`); replaces 3 per-request reads.

**`memory_pool.py`** (three separate classes, each mirrors the existing `self.use_hnd` pattern)
- `MHATokenToKVPool`: cache `use_native_move_kv_cache`; replaces the hot `_move_kv_cache_impl` read
- `MambaPool`: cache `debug_memory_pool`; replaces the `copy_from` read
- `MiniMaxSparseKVPool`: cache `use_minimax_fused_kv_index_store`; replaces the `_can_fuse_kv_index_store` read

**`mooncake_store.py`**
- Flatten `should_split_heads` alongside the already-flattened `split_factor`; replaces 3 reads.

## Verification
All changes are **pure attribute-read substitutions** (no logic change). Verified by count-based equivalence + AST parse + ruff/black/isort/codespell all pass.













<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29058397188](https://github.com/sgl-project/sglang/actions/runs/29058397188)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29058397071](https://github.com/sgl-project/sglang/actions/runs/29058397071)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
