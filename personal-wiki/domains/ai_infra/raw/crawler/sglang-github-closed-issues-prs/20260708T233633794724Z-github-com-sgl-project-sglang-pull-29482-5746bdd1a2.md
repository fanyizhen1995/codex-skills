---
source_id: sglang-github-closed-issues-prs
title: 'router(pd): cancel prefill leg when decode dispatch fails to avoid hang'
canonical_url: https://github.com/sgl-project/sglang/pull/29482
captured_at: '2026-07-08T23:36:33.794724+00:00'
content_hash: 5746bdd1a225d5f814b3ce84cfbcaafeba9d15a4ccf0de2c7fd2e56ac211440c
---
# router(pd): cancel prefill leg when decode dispatch fails to avoid hang

URL: https://github.com/sgl-project/sglang/pull/29482
State: closed
Labels: model-gateway
Closed at: 2026-07-08T07:58:52Z
Merged at: 

## Summary
In PD (prefill–decode) disaggregation, `execute_dual_dispatch_internal` dispatches a request to the prefill and decode workers concurrently with `tokio::join!(prefill.send(), decode.send())`. The prefill leg cannot complete until the decode worker's KV receiver registers via the bootstrap handshake, so when the **decode leg fails at the transport level** the prefill leg can never make progress. The unconditional `join!` then blocks on the doomed prefill leg until `request_timeout_secs` (default **1800s**), leaving an orphaned `Bootstrapping` room on the prefill worker and the request wedged with both engines idle.

We hit this reliably under high-concurrency, long-context PD warmup: a transient stall of the decode HTTP server (overwhelmed by a burst of very long-context requests) makes a subset of decode legs fail with `error sending request`; their prefill legs stay open, so those requests hang at `in_flight=N` with **GPU utilization 0%** until the 1800s timeout retries them.

### Fix
Drive both legs but resolve the decode leg first. On a decode transport error, **drop (cancel) the prefill future** (reqwest cancels the in-flight request on drop, letting the prefill worker release the orphaned `Bootstrapping` room) and return the existing retryable `502` so the dispatcher re-dispatches the pair with a fresh bootstrap room. Prefill is not penalized in the circuit breaker for a decode-driven cancellation. The success path and the decode-error-*status* path are unchanged.

## Test plan
- [x] `cargo check` passes for `sgl-model-gateway`.
- [x] 2P1D Kimi-K2.6 conc=96 long-context agentic warmup: before, warmup wedged ~30 min (`in_flight` stuck, GPU 0%) until the 1800s timeout; after, decode-leg failures retry in ms–s, warmup completes with no stall and `errors=0`, while `request_timeout_secs` can stay high (no truncation of legitimately long streaming responses).
- [ ] CI







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28277803198](https://github.com/sgl-project/sglang/actions/runs/28277803198)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28277803120](https://github.com/sgl-project/sglang/actions/runs/28277803120)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
