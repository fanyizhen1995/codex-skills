---
source_id: sglang-github-closed-issues-prs
title: '[Fix] Chain the seq_lens publish event records so prebuilt seeding keeps the
  forward fence'
canonical_url: https://github.com/sgl-project/sglang/pull/30435
captured_at: '2026-07-08T23:36:33.788898+00:00'
content_hash: 5a8d7301e289ac73c28fa0ac7a9dff46e514a13a4ee1ba94cc2b136fa6ea1bf5
---
# [Fix] Chain the seq_lens publish event records so prebuilt seeding keeps the forward fence

URL: https://github.com/sgl-project/sglang/pull/30435
State: closed
Labels: high priority, run-ci, bypass-fastfail, run-ci-extra
Closed at: 2026-07-08T20:43:10Z
Merged at: 2026-07-08T20:43:10Z

## Problem

Under overlap, `FutureMap.publish` writes `new_seq_lens` into the relay buf and records `publish_ready`; the next iteration's resolve waits that event to order its cross-stream reads (the schedule-stream gather, and the private-stream D2H copy when the backend needs `seq_lens_cpu`) against the forward-stream write.

The PD-decode prebuilt path has no forward, so it seeds the relay for its new requests by calling `publish` on the scheduler's (schedule) stream. A CUDA event holds a single capture point, so this re-record moves `publish_ready` off the forward stream and drops the fence on the in-flight forward's write.

Today this happens to stay correct on CUDA only through an implicit ordering chain: the scheduler's WAR barrier runs earlier in the same loop iteration on the same schedule stream, and workers record `read_done` after their publish, so the re-recorded event transitively inherits the forward dependency. That correctness depends on three unrelated pieces of code ordering, and on platforms where the WAR barrier is disabled it is a stale-read window for backends that consume the `seq_lens_cpu` mirror.

## Fix

Chain the records inside `publish`: before re-recording, the recording stream waits the event's previous capture point. This upgrades `publish_ready` to cumulative semantics — the event firing implies every prior publish's write is visible — which holds on any stream, for any caller, with no reliance on the WAR barrier.

- On the forward path the chain wait is a same-stream no-op (the previous record is on the same forward stream), so steady-state decode is unaffected.
- A publish off the forward stream (prebuilt seeding) now explicitly carries the in-flight forward's fence instead of dropping it.
- No caller or resolve changes; cold start (first publish is the prebuilt seed) works unchanged.

## Alternatives considered

Splitting publish into data-plane seeding without an event record (plus an explicit ordering edge for the D2H copy), or scoping that edge with a seeded flag, were prototyped. All variants share the same intrinsic cost on iterations adjacent to seeding (the seeded rows physically queue behind the schedule stream's barrier wait); the chain is the smallest self-contained version — a few lines in one function, no new parameters or state.

## Behavior notes

- CUDA: behavior-preserving, except the iteration right after a prebuilt batch now genuinely waits for the in-flight forward's publish instead of accidentally skipping the wait.
- Platforms without the WAR barrier: closes the stale-read window; resolve's wait no longer depends on the barrier being present.













<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28933863987](https://github.com/sgl-project/sglang/actions/runs/28933863987)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28933863683](https://github.com/sgl-project/sglang/actions/runs/28933863683)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
