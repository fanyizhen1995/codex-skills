---
source_id: sglang-github-closed-issues-prs
title: '[DSA] Compact indexer K cache: drop slots for skip_topk (shared) layers (+15.8%
  KV capacity on GLM-5.2)'
canonical_url: https://github.com/sgl-project/sglang/pull/30923
captured_at: '2026-07-13T23:40:05.192634+00:00'
content_hash: ae5c740662bc9db5a19af1486a4c5b50532ce04d72ab6102d2b89201617bfac7
---
# [DSA] Compact indexer K cache: drop slots for skip_topk (shared) layers (+15.8% KV capacity on GLM-5.2)

URL: https://github.com/sgl-project/sglang/pull/30923
State: closed
Labels: deepseek, npu
Closed at: 2026-07-13T04:04:18Z
Merged at: 

## Motivation

`DSATokenToKVPool` allocates an indexer K-cache slot (132 B/token/layer: 128 B fp8 index-K + 4 B scale) for **every** transformer layer. With cross-layer index-top-k sharing (GLM-5.2: 57 shared of 78 layers), shared layers reuse the previous full layer's top-k and **never read their own indexer cache** (`should_run_indexer`), so 57/78 of the indexer pool — **13.6 % of the entire KV pool, ~7.5 KB/token** — is allocated and never used. Compacting it buys **+15.8 % token capacity** on GLM-5.2 for free.

This follows TensorRT-LLM's approach of materializing indexer state only on full layers (NVIDIA/TensorRT-LLM#15574), and mirrors the compacted sparse-layer sub-pool pattern already used by `MiniMaxSparseKVPool`.

Stacked on #30922 (skip building the `Indexer` module on shared layers).

## Modifications

- **`pool_configurator.py`**: new `get_dsa_compact_indexer_layer_ids(mr)` — the single source of truth for which (absolute) layer ids own an indexer slot. Returns `None` (dense one-slot-per-layer layout, i.e. today's behavior) for: dense-DSA models (DeepSeek-V3.2), draft/NextN workers, hisparse, hierarchical cache (their host mirrors assume the dense layout), DSA cache layer split, and the `SGLANG_DSA_COMPACT_INDEXER_CACHE=false` escape hatch. Cell-size accounting uses the compact count so `max_total_num_tokens` grows accordingly.
- **`memory_pool.py` (`DSATokenToKVPool`)**: optional `indexer_layer_ids` ctor arg; buffers allocated per indexer layer; all five layer-id-based accessors route through a slot lookup that **hard-asserts on shared-layer access** (any missed call site fails loudly instead of reading garbage); cpu-offload copies and `get_state_buf_infos` enumerate the compact buffer list.
- **`model_runner_kv_cache_mixin.py`**: pass `indexer_layer_ids` to the plain `DSATokenToKVPool` only (`HiSparse`/`LayerSplit` subclasses keep the dense layout).
- **`environ.py`**: `SGLANG_DSA_COMPACT_INDEXER_CACHE` (default true).
- **`mooncake/conn.py`**: PD-disagg ships indexer buffers as a positionally-paired `StateType.DSA` ptr list; a buffer-count mismatch (e.g. compact vs dense across versions) previously fell into lenient truncation and would silently mispair layers — now it hard-fails with a clear message. Both P and D compute the layout from the same config + helper, so same-version deployments pair correctly by construction, and the DSA state transfer volume itself drops 73 % on GLM-5.2.

PP is handled: the mapping is computed per rank from `[start_layer, end_layer)`. Unsupported-path bookkeeping (hisparse host mirror, layer-split shard math, hierarchical-cache sidecar) deliberately keeps the dense layout rather than half-supporting it; they can be migrated in follow-ups.

## Accuracy Tests

8-layer GLM-5.2 config (`F F F S S S F S`, real dims, dummy weights, B200, `mem-fraction-static 0.4`):

| | main | this PR | check |
|---|---|---|---|
| KV cell size | 5664 B/token | **5136 B/token** | = 8×576 (MLA) + **4**×132 (indexer) exactly |
| `max_total_num_tokens` | 10,539,968 | **11,638,208** | **+10.4 %** (theory +10.3 %) |
| Greedy output ids | `[40472, 76288, 138027, ...]` | **identical** | full layers read/write their slots correctly |

Dense-DSA regression (same config without `index_topk_freq`): tokens and KV size **bit-identical to main** (10,539,968 / 55.60 GB) — helper returns `None`, stock layout.

Extrapolated to full GLM-5.2 (78 layers): 55,224 → 47,700 B/token ⇒ **+15.8 % KV token capacity** on every rank.

Unit tests: `test/registered/unit/mem_cache/test_dsa_compact_indexer_cache.py` (hermetic, CPU) — layer-placement resolution incl. the shipped GLM-5.2 config reproducing 21 full / 57 shared, pattern-over-freq precedence, PP ranges, and every dense-layout gate. 9/9 pass.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Provide accuracy and speed benchmark results.

cc @mattteochen @zRzRzRzRzRzRzR @mmangkad







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29185114985](https://github.com/sgl-project/sglang/actions/runs/29185114985)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29185114939](https://github.com/sgl-project/sglang/actions/runs/29185114939)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
