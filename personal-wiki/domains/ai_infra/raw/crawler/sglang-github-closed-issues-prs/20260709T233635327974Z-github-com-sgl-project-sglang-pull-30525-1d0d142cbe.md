---
source_id: sglang-github-closed-issues-prs
title: 'refactor(load-snapshot): build LoadSnapshot directly, drop legacy get_loads
  IPC'
canonical_url: https://github.com/sgl-project/sglang/pull/30525
captured_at: '2026-07-09T23:36:35.327974+00:00'
content_hash: 1d0d142cbe3099539db79d32d53cfd92094c91ce098b8dbcb29260c827d6b8e8
---
# refactor(load-snapshot): build LoadSnapshot directly, drop legacy get_loads IPC

URL: https://github.com/sgl-project/sglang/pull/30525
State: closed
Labels: run-ci, run-ci-extra
Closed at: 2026-07-09T12:58:11Z
Merged at: 2026-07-09T12:58:11Z

## Problem
`/v1/loads` built a `GetLoadsReqOutput` that was immediately converted into a `LoadSnapshot` via `from_get_loads_output()`. That IPC type, its dispatcher registration, and the flattened `has_*` / `*_` mirror fields (plus per-field numpy coercion) were pure duplication.

## Fix
- Drop `GetLoadsReqInput`, `GetLoadsReqOutput`, `handle_get_loads_req`, and the `get_loads` communicator registration.
- `SchedulerLoadInquirer.get_loads()` now returns a `LoadSnapshot` directly.
- Move `MemoryMetrics` / `SpeculativeMetrics` / `LoRAMetrics` / `DisaggregationMetrics` / `QueueMetrics` into `load_snapshot.py`; `LoadSnapshot` nests them as `Optional` fields instead of flattened mirrors.
- `to_dict()` walks a small section table; a numpy `enc_hook` on the encoder replaces per-field `_native` coercion.

The `/v1/loads` JSON response shape is unchanged.

## Test
Updated `test_v1_loads_aggregate` and `test_type_based_dispatcher`.

































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28985522740](https://github.com/sgl-project/sglang/actions/runs/28985522740)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28985522707](https://github.com/sgl-project/sglang/actions/runs/28985522707)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
