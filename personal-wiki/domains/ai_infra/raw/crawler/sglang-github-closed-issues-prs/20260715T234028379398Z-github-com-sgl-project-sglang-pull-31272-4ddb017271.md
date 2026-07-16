---
source_id: sglang-github-closed-issues-prs
title: 'feat(sgl-router): stamp selected worker on dispatch-stage errors via Server-Timing:
  engine.worker'
canonical_url: https://github.com/sgl-project/sglang/pull/31272
captured_at: '2026-07-15T23:40:28.379398+00:00'
content_hash: 4ddb0172710573b13e1dd5ce4945dadfb94e8c9d7a386e318cf0159ba8a0e22a
---
# feat(sgl-router): stamp selected worker on dispatch-stage errors via Server-Timing: engine.worker

URL: https://github.com/sgl-project/sglang/pull/31272
State: closed
Labels: 
Closed at: 2026-07-15T05:09:18Z
Merged at: 2026-07-15T05:09:18Z

## Summary

On a `dispatch`-stage `ApiError` (a worker was selected and it timed out / was unreachable / dropped mid-body / stale-cancel fired), append the selected worker's identity as its own repeated `Server-Timing` entry, exactly like `router.stage`:

```
Server-Timing: router.stage;desc=dispatch, engine.worker;desc=http://10.4.2.7:30000/
```

Lets a fronting gateway attribute an engine-owned stall to the **specific** downstream worker in a multi-worker pool, which today is invisible past the router.

## Motivation

In router mode the engine worker (`engines-<slug>` pod) sits downstream of the router and is invisible to the gateway/sidecar: `backend_pod=` (yamux) and `router.pod` (from `9ecf43cf38` / `e2a19bb1fc`) are both the *router* pod. `whyToSource()` can conclude `source=engine` on a `dispatch`-stage error, but only the router knows *which* worker it dispatched to. This surfaces that last join.

## Base branch

`combine/router-admission-http2-loadaware` (production fork branch), **not** upstream `main` — the edge-middleware rewrite `cd6dedf97` on `main` dropped the `router.stage` / `router.pod` emission this piggybacks on.

## Coverage

Dispatch-stage variants that name a worker:

| Variant | Worker field | New in this PR? |
|---|---|---|
| `UpstreamUnreachable` | `worker: reqwest::Url` | (existing) |
| `UpstreamTimeout` | `worker: reqwest::Url` | (existing) |
| `UpstreamStatus` | `worker: reqwest::Url` | **added** |
| `StaleRequestExpired` | `worker: reqwest::Url` | **added** |
| `AttemptTimeout` | — | **deliberately excluded** per spec (`_ => None`); attempt-timeout is more "attempt failed" than "this worker misbehaved" and the retry loop reassigns immediately. Add as follow-up if operators want per-attempt attribution. |

## Wiring

- `error.rs` `ApiError::into_response()` appends `engine.worker` **after** the existing `router.stage` append — same discipline as `router.pod` in `app.rs`.
- Helper `ApiError::engine_worker_server_timing() -> Option<HeaderValue>` is exhaustive (no wildcard on the enum match) for the same reason as `stage()`: a future variant is forced to decide whether it names a worker.
- Fallback to `engine.worker;desc=unknown` if the rendered URL somehow isn't a valid `HeaderValue` — mirrors `pod_server_timing()`. URLs are always valid `HeaderValue`s so this shouldn't fire, but it keeps the invariant "dispatch-stage errors that name a worker ALWAYS carry an `engine.worker` line."
- Construction sites: `proxy/mod.rs:702` (mid-body-drop) passes the `worker_url` it already parsed for `forward_json_to`. `chat.rs` (stale-cancel in streaming/unary/plain/pd arms) uses a small `worker_url_for_error(&str) -> reqwest::Url` helper for the discovery-emitted-URL → typed-Url parse; soft-fails to an `http://unknown/` placeholder if parse fails (won't in practice — discovery would have tripped the breaker upstream).

## Test plan

- [x] `cargo test --lib server::error::tests` — new tests:
  - `dispatch_stage_error_carries_engine_worker_and_router_stage_together` — verifies both `router.stage;desc=dispatch` and `engine.worker;desc=<url>` appear as separate `Server-Timing` values (mirrors `response_carries_router_pod_server_timing_without_clobbering` from `app.rs`).
  - `non_dispatch_stage_error_omits_engine_worker` — behavioral lock-in that an ingress/queue-stage error must not carry `engine.worker`.
- [x] `router_originated_scenarios_match_status_and_headers` (existing table test) — extended `UpstreamStatus` and `StaleRequestExpired` cases with `worker` field, still passing.

**Note**: the branch has an unrelated pre-existing compile error in `tokenizer/adapter.rs:219` (`.with_extend(true)` on a `Result` — introduced by `718cc0cae2c` on 2026-07-08, part of the fastokens L1 cache work) that blocks the full workspace `cargo test`. My changes compile cleanly for the touched files; the pre-existing tokenizer issue is out of scope here.

## Consumer already staged

No further gateway work needed to unblock this — [radixark PR #911](https://github.com/radixark/gpu-platform-proto/pull/911) landed the parse seam for `router.stage` / `router.pod`; adding `engine.worker` is a ~10-line addition mirroring `StampRouterPod` (log field + optional reverse-map to pod name against the tracked endpoints).















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29387694140](https://github.com/sgl-project/sglang/actions/runs/29387694140)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29387694109](https://github.com/sgl-project/sglang/actions/runs/29387694109)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
