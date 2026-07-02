---
source_id: sglang-github-closed-issues-prs
title: '[bug2] skip swa recovery on locked full kv'
canonical_url: https://github.com/sgl-project/sglang/pull/29352
captured_at: '2026-07-01T02:12:08.953712+00:00'
content_hash: 7441dc6ebecfdf87c4054565bc1233cdcdfeb782ae96f7efca81c2b875e688ac
---
# [bug2] skip swa recovery on locked full kv

URL: https://github.com/sgl-project/sglang/pull/29352
State: closed
Labels: high priority, run-ci, bypass-fastfail
Closed at: 2026-06-30T23:07:07Z
Merged at: 2026-06-30T23:07:07Z

Split 3/5 from https://github.com/sgl-project/sglang/pull/29349

## Motivation
This PR fixes an SWA recovery path that could overwrite Full KV still protected by an active request.

SWA may try to recover a tombstoned SWA component from fresh insert data. That recovery must not replace the node's Full KV if the Full component is still locked.

## Modifications
When recovering SWA state from an insert overlap and the node's Full component has `lock_ref > 0`, preserve the locked Full KV value, but still restore the SWA component from the incoming KV slice and update the Full-to-SWA mapping.

### Bugs & Fixes

#### Bug 2: SWA recovery could overwrite locked Full KV
  - **Root cause:** SWA tombstone recovery could free and replace the node's Full KV without checking whether the Full component was still locked by an active request.
  - **Fix:** Add the locked-Full guard so SWA recovery does not free or replace Full KV when `Full.lock_ref > 0`.
  - **Commit:** 31ce0e5f38

#### Follow-up: make the split PR standalone
  - **Root cause:** The first split only guarded against overwriting locked Full KV by skipping SWA recovery when `Full.lock_ref > 0`. This protected Full KV, but could leave the node with valid Full state and missing SWA state.
    - Then `insert()` could accept a prefix that `cache_unfinished_req()`'s follow-up `match_prefix()` rejects, causing `new_prefix_len > len(new_indices)`.
  - **Fix:** Preserve the locked Full KV, but still restore SWA from the incoming KV slice and update the Full-to-SWA mapping. Free only the incoming Full KV slice.
  - **Commit:** 0e6e28c086






















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28477637810](https://github.com/sgl-project/sglang/actions/runs/28477637810)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28477637493](https://github.com/sgl-project/sglang/actions/runs/28477637493)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
