---
source_id: sglang-github-closed-issues-prs
title: Fix pipeline-parallel abort missing in-flight requests in non-current microbatch
  slots
canonical_url: https://github.com/sgl-project/sglang/pull/29405
captured_at: '2026-07-10T23:37:20.335218+00:00'
content_hash: 5dcf1cfea9ad7346dbde8bc8a6c8aed03732e2a81ace91a140ac7873171e8456
---
# Fix pipeline-parallel abort missing in-flight requests in non-current microbatch slots

URL: https://github.com/sgl-project/sglang/pull/29405
State: closed
Labels: 
Closed at: 2026-07-10T00:53:19Z
Merged at: 2026-07-10T00:53:19Z

TODO: add co-author of those 2 prs when merging

## Problem

`abort_request`'s "abort already-running requests" path only scanned `self.running_batch` plus a stale `self.cur_batch`. Under pipeline parallelism the scheduler keeps per-microbatch-slot state in `running_mbs[]` / `mbs[]`, and at abort time `self.running_batch` is aliased to just the *current* microbatch slot while `self.cur_batch` holds the *previous* step's batch. So an abort (or `abort_all`) only reached requests in the current slot and the previous one — requests decoding in any other slot's `running_mbs` (or still in flight in `mbs`) were never marked `FINISH_ABORT` and kept running to completion.

This only manifests with **more than two** microbatch slots, since with two the current and previous slots already cover both.

## Fix

Under PP, scan every `running_mbs` and `mbs` slot (deduped by request); the non-PP path keeps scanning `running_batch` + `cur_batch` as before.

## Test

Adds a scripted-runtime regression test (`pp_size=4`, `pp_max_micro_batch_size=1`) that forces one decode request into each microbatch slot and asserts `abort_all` releases all of them: `test/manual/scheduler/test_scripted_pp_abort.py`. Without the fix the test fails (requests in non-current slots keep their KV); with the fix it passes. RED/GREEN evidence is attached as a comment.

## Related work

This bug was previously investigated in:
- #21300 (@burling) — earlier attempt; does not account for the other microbatch slots' `reqs`, and has no scripted-runtime test.
- #28881 (@zhaotyer) — reasonable, but bundles unrelated fixes. This PR unifies the slot scan into a single deduped loop and adds a focused scripted-runtime regression test.





























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29060817532](https://github.com/sgl-project/sglang/actions/runs/29060817532)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29060817522](https://github.com/sgl-project/sglang/actions/runs/29060817522)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
