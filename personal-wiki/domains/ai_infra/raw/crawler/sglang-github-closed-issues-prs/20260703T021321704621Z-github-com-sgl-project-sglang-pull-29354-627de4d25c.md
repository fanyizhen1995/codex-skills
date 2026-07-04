---
source_id: sglang-github-closed-issues-prs
title: '[bug6] clear stale mamba cow source on rematch'
canonical_url: https://github.com/sgl-project/sglang/pull/29354
captured_at: '2026-07-03T02:13:21.704621+00:00'
content_hash: 627de4d25c89f9fb42d9ad7a27c179a5ca73131c96d2ef2359bbd93a7db4129a
---
# [bug6] clear stale mamba cow source on rematch

URL: https://github.com/sgl-project/sglang/pull/29354
State: closed
Labels: run-ci, run-ci-extra
Closed at: 2026-07-02T05:04:10Z
Merged at: 2026-07-02T05:04:10Z

Split 5/5 from https://github.com/sgl-project/sglang/pull/29349 (updated according to the review)

## Motivation
This PR fixes stale deferred Mamba COW metadata after scheduler admission rejects a waiting request.

`init_next_round_input()` can prepare Mamba COW/clear metadata before `add_one_req()` decides whether the request is actually admitted into the next batch. If admission fails, that per-attempt metadata must be rolled back together with the temporary Mamba slot.

## Modifications
When `add_one_req()` rejects a request, clear the deferred Mamba metadata prepared for that admission attempt:
  - `mamba_cow_src_index`
  - `mamba_needs_clear`

The existing temporary `mamba_pool_idx` rollback is kept, with the session guard preserved so session-owned Mamba slots are not freed by this path.

### Bugs & Fixes

#### Bug 6: rejected admission could leave stale Mamba COW metadata
  - **Root cause:** `init_next_round_input()` can set `mamba_cow_src_index` before scheduler admission is finalized. If `add_one_req()` later rejects the request, the scheduler rolls back the temporary Mamba slot but previously left the deferred COW/clear metadata intact. On a later retry, the request could copy from stale or freed Mamba state instead of recomputing the correct metadata.
  - **Fix:** On rejected admission, clear `mamba_cow_src_index` and reset `mamba_needs_clear`, while preserving the existing non-session temporary-slot rollback.
  - **Commit:** `1c984726aa`

































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28494335479](https://github.com/sgl-project/sglang/actions/runs/28494335479)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28494335411](https://github.com/sgl-project/sglang/actions/runs/28494335411)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
