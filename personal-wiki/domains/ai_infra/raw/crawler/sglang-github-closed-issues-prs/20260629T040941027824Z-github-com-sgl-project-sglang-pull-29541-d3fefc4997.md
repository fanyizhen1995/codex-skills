---
source_id: sglang-github-closed-issues-prs
title: '[Spec] Publish DFLASH verify read-done event for fine-grained WAR barrier'
canonical_url: https://github.com/sgl-project/sglang/pull/29541
captured_at: '2026-06-29T04:09:41.027824+00:00'
content_hash: d3fefc4997ebbdeb0f9e00ed45d839ef21ef9d3b4ca229f4f8e06be83e17beee
---
# [Spec] Publish DFLASH verify read-done event for fine-grained WAR barrier

URL: https://github.com/sgl-project/sglang/pull/29541
State: closed
Labels: blackwell, run-ci
Closed at: 2026-06-29T01:51:39Z
Merged at: 2026-06-29T01:51:39Z

## What

Publish the WAR `read_done` event from the DFLASH target-verify forward so the scheduler's global `_apply_war_barrier` takes the fine-grained `wait_event(read_done)` fast path instead of the coarse `wait_stream(forward_stream)` fallback.

## Why it is valid

The target-verify cuda graph builds its page table in `load_batch` (pre-replay) and then replays reading only that static snapshot. So the forward finishes reading the shared `req_to_token` / SWA buffers *before* replay — `read_done` is recorded at exactly that point, so it is a sound WAR signal.

## WAR ordering

The over-alloc write to `req_to_token` (plan stream) stays ordered after the previous forward's read through this chain:

```
read_done  (recorded on the forward stream, after req_to_token is read)
   │  decode_cuda_graph_runner: war_fastpath_read_done_event = read_done
   ▼
schedule_stream.wait_event(read_done)         scheduler.py:1521  (_apply_war_barrier, called at loop top :1578)
   │
   ▼
plan_stream.wait_stream(schedule_stream)      dflash_info_v2.py:188  (prepare_for_decode)
   │
   ▼
over-alloc writes req_to_token (plan stream)  dflash_info_v2.py:218
```

`prepare_for_decode` already does `plan_stream.wait_stream(schedule_stream)` (originally to see the scheduler's filter/merge writes), so the plan-stream over-alloc write inherits the `read_done` dependency transitively — no explicit plan-stream wait is added. The barrier now waits only until `req_to_token` has been read (start of the verify forward) instead of the whole forward, recovering the overlap window the coarse fallback serialized.

## Dependencies

Builds on #29556 (merged) — removed `verify_done` and the dflash `_war_barrier_enabled` opt-out, routing dflash through `_apply_war_barrier`. Independent of #29343 (fa3).















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28342455012](https://github.com/sgl-project/sglang/actions/runs/28342455012)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28342454942](https://github.com/sgl-project/sglang/actions/runs/28342454942)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
