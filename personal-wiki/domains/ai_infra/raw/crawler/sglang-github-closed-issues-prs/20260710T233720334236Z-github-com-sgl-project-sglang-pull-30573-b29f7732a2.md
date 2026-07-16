---
source_id: sglang-github-closed-issues-prs
title: Configurable decode retraction order
canonical_url: https://github.com/sgl-project/sglang/pull/30573
captured_at: '2026-07-10T23:37:20.334236+00:00'
content_hash: b29f7732a2d6c1e47cb3ab52166ace1aedb4503c56120ed283173f37c4b0f7d5
---
# Configurable decode retraction order

URL: https://github.com/sgl-project/sglang/pull/30573
State: closed
Labels: run-ci
Closed at: 2026-07-10T00:55:27Z
Merged at: 2026-07-10T00:55:27Z

## Motivation

When the KV cache fills during decode, requests are retracted to free memory. The existing policy always retracts short-output, long-input requests first, which is not always desirable — some deployments want to retract lower-priority work first.

## Changes

- Add a `--retraction-policy` server arg with two choices:
  - `length` (default): preserves the existing behavior.
  - `priority`: retracts lower-priority requests first, using the same priority direction as priority scheduling (`--schedule-low-priority-values-first`), with the length key as a tiebreaker. Requires `--enable-priority-scheduling`.
- Extract the retraction ordering into `ScheduleBatch._get_decode_retraction_order` so it can be unit-tested directly, while keeping the back-of-batch-only retraction path required for speculative decoding.
- Validate that `--retraction-policy priority` is only used together with `--enable-priority-scheduling`.
- Add unit tests covering both policies, the priority direction, the length tiebreaker, and the spec-decode path.

## Original commits

- `6aba50ba9`







































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29043394927](https://github.com/sgl-project/sglang/actions/runs/29043394927)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29043394666](https://github.com/sgl-project/sglang/actions/runs/29043394666)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
