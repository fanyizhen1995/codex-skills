---
source_id: sglang-github-closed-issues-prs
title: 'AssertionError: dec_lock_ref on node with node.swa_lock_ref=0 in SWARadixCache
  under DeepSeek-V4 long-context workload'
canonical_url: https://github.com/sgl-project/sglang/issues/24153
captured_at: '2026-07-13T23:40:05.156442+00:00'
content_hash: fb8b6fb38be39ac83e1abfaa922b27d8386ed983df7d1b463f09059cf47006d7
---
# AssertionError: dec_lock_ref on node with node.swa_lock_ref=0 in SWARadixCache under DeepSeek-V4 long-context workload

URL: https://github.com/sgl-project/sglang/issues/24153
State: closed
Labels: inactive
Closed at: 2026-07-13T00:36:20Z
Merged at: 

## Title

`AssertionError: dec_lock_ref on node with node.swa_lock_ref=0` in SWARadixCache under DeepSeek-V4 long-context workload

## Summary

Running a DeepSeek-V4-Pro deployment on long-context workloads (prompts in the ~100K–500K token range, with substantial cross-request shared prefix) we intermittently hit an assertion failure inside `SWARadixCache.dec_lock_ref`. The scheduler crashes; all TP ranks hit the same `node.id` simultaneously, suggesting deterministic divergence rather than a races condition.

The crash is **probabilistic** — server runs cleanly for a while (tens of minutes to hours), then fails on a normal `cache_finished_req` path. Once it triggers, every subsequent attempt to release that request crashes the scheduler.

## Stack trace

```
[TP5 EP5] Scheduler hit an exception: Traceback (most recent call last):
  File ".../managers/scheduler.py", line 3027, in run_scheduler_process
    scheduler.event_loop_overlap()
  File ".../managers/scheduler.py", line 1137, in event_loop_overlap
    pop_and_process()
  File ".../managers/scheduler.py", line 1108, in pop_and_process
    self.process_batch_result(tmp_batch, tmp_result)
  File ".../managers/scheduler.py", line 2472, in process_batch_result
    self.process_batch_result_decode(batch, result)
  File ".../managers/scheduler_output_processor_mixin.py", line 438, in process_batch_result_decode
    release_kv_cache(req, self.tree_cache)
  File ".../mem_cache/common.py", line 469, in release_kv_cache
    tree_cache.cache_finished_req(req, is_insert=is_insert)
  File ".../mem_cache/swa_radix_cache.py", line 517, in cache_finished_req
    self.dec_lock_ref(
  File ".../mem_cache/swa_radix_cache.py", line 807, in dec_lock_ref
    node.swa_lock_ref > 0
AssertionError: dec_lock_ref on node with node.swa_lock_ref=0, node.id=291371
```

The same `node.id` is hit on all TP ranks (TP0..TP7) within the same forward step.

## Environment

- Model: `deepseek-ai/DeepSeek-V4-Pro` (`num_hidden_layers=61`, `sliding_window=128`, `page_size=256`)
- Hardware: 8× B200, TP=8, EP=8
- Speculative decoding: EAGLE, `--speculative-num-steps 3 --speculative-eagle-topk 1 --speculative-num-draft-tokens 4`
- `--chunked-prefill-size 4096`
- `--max-running-requests 20`
- `--swa-full-tokens-ratio 0.1`
- `--context-length 512000`
- `--attention-backend compressed`
- `--mem-fraction-static 0.85`
- `--kv-cache-dtype fp8_e4m3`
- Hybrid SWA memory enabled (default)
- Radix eviction: `lru` (default)
- Overlap schedule enabled (default)

Env variables left at their defaults:

- `SGLANG_OPT_SWA_RADIX_CACHE_COMPACT` (default `True`)
- `SGLANG_OPT_SWA_RELEASE_LEAF_LOCK_AFTER_WINDOW` (default `False`)

## Workload pattern that triggers it

- Mix of long prompts (≈ 100K–500K tokens) and shorter prompts.
- Multiple long-prompt requests share **very long common prefixes** (e.g. several requests differing only in the last few hundred tokens out of ~485K).
- Stream of requests over time so the SWA prefix-cache is exercised continuously (insert / match / evict / tombstone).
- Some requests generate enough output that `decode_position` advances past `sliding_window` (i.e. workload would exercise the early SWA-leaf release path if `SGLANG_OPT_SWA_RELEASE_LEAF_LOCK_AFTER_WINDOW=True` were enabled, but we leave it at the default `False`).

We have not been able to reduce this to a small standalone reproducer yet — empirically the crash needs the SWA radix tree to grow large (the `node.id` counter at crash time is in the hundreds of thousands, indicating a lot of accumulated insert / split / tombstone activity) and a workload that simultaneously evicts SWA pages and does cross-request prefix matching.

## What the assertion implies

The failure is at `swa_radix_cache.py:807`:

```python
assert (
    node.swa_lock_ref > 0
), f"dec_lock_ref on node with {node.swa_lock_ref=}, {node.id=}"
```

i.e. `dec_lock_ref` walks past the request's `swa_uuid_for_lock` boundary into a node that was never (or is no longer) SWA-locked. So either:

1. `swa_uuid_for_lock` recorded at `inc_lock_ref` time can no longer be found on the dec walk (uuid lost / overwritten by a tree mutation between inc and dec), or
2. `swa_lock_ref` accounting got out of sync with the chain shape due to a tree mutation (split / compact / tombstone) that happened while a request was holding a lock.

We've eyeballed the obvious candidates (`_split_node`, `_compact_single_child_chain`, `_tombstone_internal_node`, `dec_swa_lock_only`) but haven't been able to definitively pin it.

## Reproduction notes

- Repro frequency: roughly every few hours under steady production-like workload. We do **not** have a deterministic minimal repro.
- The crash dump's request list shows ~35 finished + ~15 unfinished requests in flight at crash time, with several long-prompt requests sharing prefixes ≥ 480K tokens.
- All TP ranks fail on identical `node.id`, which suggests the divergent state is in the radix tree itself, not in any per-rank scheduling decision.

Happy to share more dump data or add logging if it helps narrow this down. Let us know what would be most useful.
