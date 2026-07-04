---
source_id: sglang-github-closed-issues-prs
title: '[mem_cache] Deduplicate dead DSA indexer buffers for skip-topk layers (opt-in)'
canonical_url: https://github.com/sgl-project/sglang/pull/30041
captured_at: '2026-07-04T02:13:49.132613+00:00'
content_hash: f0a2d36163715150ed7529a1a9bbd3f5974cce0cacbf45a28b1e8ee23ab7b1e8
---
# [mem_cache] Deduplicate dead DSA indexer buffers for skip-topk layers (opt-in)

URL: https://github.com/sgl-project/sglang/pull/30041
State: closed
Labels: 
Closed at: 2026-07-03T13:06:38Z
Merged at: 

## Motivation

DSA models with `index_topk_freq > 1` run the indexer only on a subset of layers. The skip-topk ("shared") layers carry **no indexer weights in the checkpoint and never run the indexer** (`attention_forward_methods/forward_mla.py` returns before the indexer for them) — yet `DSATokenToKVPool` allocates a full `index_k_with_scale_buffer` for **every** layer. Those buffers have no writer and no reader: dead VRAM at 132 B/token/layer.

On GLM-5.2 (79 layers, 22 with indexer weights) this is ~7.5 KB/token of dead device memory, plus the same dead layers mirrored in the `DSAIndexerPoolHost` sidecar and its storage page format.

## Change (opt-in: `SGLANG_DSA_COMPACT_INDEXER=1`)

- `dsa_compact_indexer_layer_mask()` derives a per-layer mask from the config with **exactly the model's skip_topk gate priority** (`index_topk_pattern` > `index_skip_topk_offset` > `index_topk_freq`), and cross-checks it against `indexer_types` when present — any mismatch falls back to stock allocation (fail-safe, with a warning).
- Skip-topk layers all point at **one shared full-size alias tensor**, so every full-layer-sweep code path (`move_kv_cache`, retract offload, host backup) stays in-bounds while only `n_full + 1` buffers consume VRAM. `get_kv_size_bytes` counts the alias once.
- `DSAIndexerPoolHost` mirrors only the real indexer layers — the host sidecar, its L3 page format, and the transfer arithmetic shrink in lockstep (`layer_id` in the host pool is the local/compact index; device access translates through `indexer_layer_ids`).
- `pool_configurator` cell-size accounting matches the actual allocation, so the freed VRAM becomes additional KV pool tokens.
- Partial pools are never compacted: the single-layer NEXTN draft pool owns real indexer weights, so the mask derivation returns `None` unless the pool spans the full model from layer 0.

## Verification

- **Unit tests** (`test/registered/unit/mem_cache/test_dsa_compact_indexer_unit.py`, CPU): mask derivation (freq / pattern priority / offset), fail-safe on contradictory `indexer_types`, partial-pool exclusion, alias identity + full shape retention, `get_kv_size_bytes` alias dedup. 10/10 pass.
- **Production serving** (GLM-5.2 W4AFP8, 8×H100, TP8+DP-attention): boot-time pool grows **+5.8 % at an equal memory budget** (the freed memory shows up directly as `max_total_num_tokens`), host indexer sidecar **26.3 GB → 7.5 GB per rank (−72 %)**, decode throughput unchanged (512-token streaming decode at 264K context: 81–102 tok/s before and after), multi-day serving with mixed cold/warm traffic and no correctness regressions.
- Off by default — with the env unset, allocation is byte-identical to stock (covered by a unit test).

## Notes for reviewers

- The mask **must** equal the set of layers that actually touch `index_k` — a mismatch would silently corrupt topk for a live layer. That is why derivation mirrors `models/deepseek_v2.py` exactly and `indexer_types` is used as a cross-check rather than a source.
- HiSparse pools do not forward the new kwarg (mutually exclusive by design for now); extending the compaction to `HiSparseDSATokenToKVPool.index_buf` is a natural follow-up and also lifts the single-node `host_to_device_ratio` ceiling.

🤖 Generated with [Claude Code](https://claude.com/claude-code)







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28660384206](https://github.com/sgl-project/sglang/actions/runs/28660384206)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28660384031](https://github.com/sgl-project/sglang/actions/runs/28660384031)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
