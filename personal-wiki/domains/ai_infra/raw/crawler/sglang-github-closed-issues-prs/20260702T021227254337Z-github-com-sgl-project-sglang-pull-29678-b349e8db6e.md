---
source_id: sglang-github-closed-issues-prs
title: 'feat(mem_cache): unified memory pool for hybrid Mamba / SWA models'
canonical_url: https://github.com/sgl-project/sglang/pull/29678
captured_at: '2026-07-02T02:12:27.254337+00:00'
content_hash: b349e8db6e28341a6835644f0e759687d7a2cb63a811f463d19b37dba90ffc12
---
# feat(mem_cache): unified memory pool for hybrid Mamba / SWA models

URL: https://github.com/sgl-project/sglang/pull/29678
State: closed
Labels: documentation, npu, bypass-fastfail, run-ci-extra
Closed at: 2026-07-01T20:21:59Z
Merged at: 2026-07-01T20:21:59Z

## Motivation

Hybrid **Mamba/GDN** and hybrid **SWA** models maintain two caches: the full-attention KV cache and the per-request Mamba conv/SSM (or SWA) state. Today each lives in a separately-sized pool, so the capacity split between them is fixed at startup — one can run dry while the other has slack.

This PR adds opt-in `--enable-unified-memory`: a single contiguous `uint8` byte buffer is split between the full-attention KV sub-pool and the state sub-pool by a `MultiEndedAllocator` that grows them from opposite ends, so the split flexes with the workload instead of being fixed at init. Built on the page-major layout (#29533, merged into main); the flag implies `--enable-page-major-kv-layout`.

## Modifications

- **`mem_cache/unified_memory_pool.py`** — `UnifiedKVPool` (the one byte buffer) with `MHASubPoolSpec` / `MambaSubPoolSpec` per-slot layouts; the sub-pools `UnifiedMHATokenToKVPool` / `UnifiedSWAKVPool` (full-attention & SWA KV) and `UnifiedMambaPool` (conv/SSM state); plus `UnifiedMambaSlotAllocator` and `UnifiedHybridReqToTokenPool`. Factories `init_unified_mamba_pools` / `init_unified_swa_pools` build the whole stack from one buffer.
- **`mem_cache/multi_ended_allocator.py`** — `MultiEndedAllocator` (one per sub-pool), composed into `UnifiedMambaTokenToKVPoolAllocator` / `UnifiedSWATokenToKVPoolAllocator`: the two sub-allocators grow toward each other from opposite ends, each owning its virtual↔physical page tables and doing lazy compaction (table remaps only, no reference rewriting).
- **`mem_cache/triton_ops/virtual_slot.py`** — Triton kernel for the in-place virtual→physical page bind on alloc.
- **Pools are pure stores; write-locs travel in metadata.** All write-location info travels in the attention metadata as `KVWriteLoc{loc, swa_loc, full_loc}`. The unified pool's full-attention and SWA write targets are pre-translated virtual→physical and carried on the Triton backend's `ForwardMetadata` (`out_cache_loc_full_physical`, `swa_out_cache_loc`), resolved once per forward; the pools never translate — they write the physical loc directly. Reads resolve via the allocator's `translate_kv_loc` / `HybridReqToTokenPool.translate_mamba_indices`.
- **cuda-graph — zero in-graph translate nodes.** All virtual→physical read- and write-path translates run **eagerly** in `init_forward_metadata_out_graph` (replay-prep, before `graph.replay()`, reading the live v2p table) into capture-stable buffers, so the captured graph reads/writes already-physical locations and records no translate ops. The decode Mamba track-save reads a backend-owned static `ForwardMetadata.mamba_track_indices` buffer (refreshed in-place each replay), so the runner's InputBuffer registry slot is never mutated.
- **Admission accounting (`schedule_policy.PrefillAdder`)** — reserves the shared-gap byte cost per new Mamba slot against the joint budget, and additionally gates new Mamba slots on a Mamba-recoverable budget (shared gap + peer-compaction holes + Mamba-evictable radix) so `full_evictable` bytes can't "cover" a slot the allocator can't realize; `alloc_req_slots` is fail-loud.
- **`server_args`** — the `--enable-unified-memory` flag + validators (requires Triton attention / linear-attn / Mamba backends; monolithic decode cuda-graph only; rejects PD disaggregation, speculative decoding, hierarchical cache, decode context-parallel). Implies `--enable-page-major-kv-layout`.
- Scheduler / schedule-policy / invariant-checker plumbing for the unified pool's byte-coordinated stats and leak invariants.
- **Tests** — `MultiEndedAllocator`, the virtual-slot Triton kernel, layout compatibility, unified-mamba views, and the write-path routing contract (`test_full_loc_fast_path.py`).

## Accuracy Tests

GSM8K (200 questions, Triton backend, cuda-graph ON), unified pool vs non-unified baseline:

| Model | Path | Baseline | Unified pool |
|---|---|---|---|
| Qwen3.5-4B | hybrid GDN (Mamba) | 0.870 | **0.870** |
| Qwen3.5-35B-A3B | hybrid GDN (Mamba) | — | **0.90+** |
| gpt-oss-20b | hybrid-SWA MoE | 0.520 | **0.525** |

Also confirmed on Falcon-H1 (Mamba2) and gemma-4 (SWA).

## Speed Tests and Profiling

Not yet benchmarked — this PR is a memory-efficiency / correctness foundation. The unified buffer lets KV-vs-state capacity flex at runtime; throughput / utilization benchmarking of the enabled path is a follow-up.

## Notes / follow-ups

- Builds on the page-major KV/state layout (#29533), merged into main — this PR is based on `main` and contains only the unified-memory-pool changes.
- Constraints: requires `--attention-backend triton --linear-attn-backend triton --mamba-backend triton`; monolithic (decode) cuda-graph capture only; not yet compatible with PD disaggregation or speculative decoding. SWA / Mamba2-mixer models (gpt-oss-20b, Falcon-H1) currently need `--cuda-graph-backend-prefill disabled`.
- The HiCache Mamba offload/restore path is wired (via the `_mamba_translate` hook) but gated off / not exercised by the accuracy runs above.

## Checklist

- [x] Format code with pre-commit
- [x] Add unit tests (allocator, kernels, layout-compat, write-path routing)
- [x] Accuracy results provided (above); speed benchmarking is a follow-up
- [x] Follow SGLang code style

























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28482556388](https://github.com/sgl-project/sglang/actions/runs/28482556388)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28482556367](https://github.com/sgl-project/sglang/actions/runs/28482556367)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
