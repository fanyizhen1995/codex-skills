---
source_id: sglang-github-closed-issues-prs
title: Fix DP-attention SHM feature finalization race
canonical_url: https://github.com/sgl-project/sglang/pull/29543
captured_at: '2026-06-29T04:09:41.035773+00:00'
content_hash: 587ffc3344c74dc1229f7e62c9c0e159c295c1df72b29eb176894792f3ee4c50
---
# Fix DP-attention SHM feature finalization race

URL: https://github.com/sgl-project/sglang/pull/29543
State: closed
Labels: run-ci
Closed at: 2026-06-28T04:36:59Z
Merged at: 2026-06-28T04:36:59Z

## Motivation

Under DP-attention, the broadcast source rank returns with its original
objects while peer ranks may still be unpickling `ShmPointerMMData`
(`shm_open`).  Previously the SHM barrier only covered the non-DP-attention
path — under DP-attention no synchronization was performed, so
`materialize()` / `shm_unlink` could race with peers still opening the
shared memory segment.

## Changes

Fix by synchronizing on the same CPU groups (`attn_tp`, `attn_cp`) that
carried the SHM-backed work requests, rather than skipping the barrier
entirely under DP-attention.  The non-DP-attention path retains its
existing `tp_cpu_group` barrier.

Adds unit tests covering all three paths:
- DP-attention with both `attn_tp` and `attn_cp` groups
- Non-DP-attention with `tp_cpu_group`
- No-SHM-features skip (no barrier)

## Original commits

- `60bd82779d`

















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28311128177](https://github.com/sgl-project/sglang/actions/runs/28311128177)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28311128133](https://github.com/sgl-project/sglang/actions/runs/28311128133)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
