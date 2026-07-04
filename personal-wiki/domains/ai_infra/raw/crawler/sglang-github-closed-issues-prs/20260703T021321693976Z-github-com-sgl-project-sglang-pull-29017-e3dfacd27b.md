---
source_id: sglang-github-closed-issues-prs
title: '[model-gateway] PD router: cancel paired decode when prefill fails'
canonical_url: https://github.com/sgl-project/sglang/pull/29017
captured_at: '2026-07-03T02:13:21.693976+00:00'
content_hash: e3dfacd27b2747829cdaa14d403e0c0580e632de67b9451a4f32c96fbd0cc71b
---
# [model-gateway] PD router: cancel paired decode when prefill fails

URL: https://github.com/sgl-project/sglang/pull/29017
State: closed
Labels: model-gateway
Closed at: 2026-07-03T00:03:14Z
Merged at: 2026-07-03T00:03:14Z

## Motivation

In PD (prefill/decode) disaggregation the HTTP router (`PDRouter::execute_dual_dispatch_internal`) sends each request to a **prefill** and a **decode** worker concurrently and waits for both with `tokio::join!`.

In PD, the decode worker cannot produce a single token without the KV cache transferred from prefill. So when the **prefill request fails** — a transport error, a 4xx, or a 5xx (e.g. a prefill instance overloaded / crashed / unreachable) — the paired decode request can never make progress. It blocks in `KVPoll.WaitingForInput` until `SGLANG_DISAGGREGATION_WAITING_TIMEOUT` (default **300s**), holding a decode slot the entire time. Today the router still waits in `tokio::join!` for that decode request, so it also stalls.

Under load this is an amplifier: a burst of prefill failures leaves many decode requests each pinned for 300s, starving decode concurrency and slowing recovery long after the prefill disruption is over.

## Changes

`execute_dual_dispatch_internal` now drives prefill and decode with `tokio::select!` (in the same task) instead of `tokio::join!`:

- Both futures still start together — PD requires the decode-side receiver to be up for prefill's KV send.
- The moment prefill resolves to a **non-2xx** response or a transport error, we drop the in-flight decode future. Closing the decode HTTP connection makes the decode engine's `tokenizer_manager` detect the disconnect (it polls `is_disconnected` every `_REQUEST_STATE_WAIT_TIMEOUT`, 4s) and call `abort_request()`, freeing the stuck request in **~4-8s instead of 300s**.
- On prefill **success**, behaviour is unchanged: decode is awaited and processed exactly as before.
- Prefill error responses are shaped by the existing `process_prefill_response`, so a 4xx is forwarded with its real status and 5xx / transport errors become 502/5xx.

Scope: HTTP PD router only; no wire-format or decode-side change.

## Compatibility with existing behaviour

This change is deliberately conservative about not regressing prior fixes:

- **Upstream cancel (#19524) preserved.** Both futures stay in the request handler task — **no `tokio::spawn`**. So a client disconnect still drops the handler and cancels the pending decode request with it, for non-streaming requests too. (An earlier draft used `tokio::spawn`; it orphaned decode and let it run a full generation after the client was gone — the opposite of this PR's goal. The `select!` form avoids that.)
- **Breaker attribution preserved.** Prefill is ticked by its real status (4xx = client fault). Decode is intentionally **not** recorded when it is cancelled solely because of a prefill fault, so a prefill error storm cannot cascade and trip healthy decode workers' circuit breakers. The `BreakerOutcomesRecorded` marker still tells the outer dispatcher to skip its own recording.
- The downstream decode-response handling (`match decode_result { ... }`, `BreakerTrackedStream`, logprob merge, streaming) is untouched — only how `decode_result` is obtained changed, and its type is identical.

This complements the engine-side fix #28651 (mooncake `prefill -> decode` abort notification): the **router** covers prefill HTTP failures / unreachable prefill; the **engine** path covers a prefill that returns 2xx but then fails the KV transfer.

## Tests

Verified on a live **1P1D mooncake deployment** (Qwen3-14B-FP8, sglang v0.5.12, prefill + decode + this router in PD mode):

| Case | Result |
| --- | --- |
| Normal request (non-stream / stream) | 200, normal generation — no regression |
| Prefill returns 5xx | router returns 503 in ~0.4s; log `Prefill failed, aborting paired decode request`; decode logs `Aborted by AbortReq` ~4s later (vs 300s) |
| Prefill process crash (connection refused) | router returns 502 fast + aborts decode + retries; no hang/panic |
| Client disconnects mid non-stream generation | decode cancelled ~1s after disconnect (a `tokio::spawn` draft instead ran the full generation — fixed by the `select!` form) |
| Client disconnects mid stream | existing `Client disconnected, cancelling upstream PD stream` path still fires |

`cargo`/release build clean.























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28222125059](https://github.com/sgl-project/sglang/actions/runs/28222125059)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28222125041](https://github.com/sgl-project/sglang/actions/runs/28222125041)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
