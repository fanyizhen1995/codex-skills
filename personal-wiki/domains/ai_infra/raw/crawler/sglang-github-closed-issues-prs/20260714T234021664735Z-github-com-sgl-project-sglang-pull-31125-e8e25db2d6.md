---
source_id: sglang-github-closed-issues-prs
title: 'Disable flaky DSV4-Flash FP4 BCG determinism test (nondeterminism from #30898
  idle-rank dummy extend)'
canonical_url: https://github.com/sgl-project/sglang/pull/31125
captured_at: '2026-07-14T23:40:21.664735+00:00'
content_hash: e8e25db2d6a1d9aa39198e36899738373dfc15c00b3138c064e82958d51c67d3
---
# Disable flaky DSV4-Flash FP4 BCG determinism test (nondeterminism from #30898 idle-rank dummy extend)

URL: https://github.com/sgl-project/sglang/pull/31125
State: closed
Labels: deepseek
Closed at: 2026-07-14T23:21:11Z
Merged at: 2026-07-14T23:21:11Z

## Summary

Disables the flaky `TestDSV4FlashFP4BreakableCudaGraphB200.test_determinism_temp_zero` (`'Paris.' != 'Paris'`, e.g. [this scheduled run](https://github.com/sgl-project/sglang/actions/runs/29292733629/job/86961435737)) to unblock per-commit CI. This is a **stopgap** — a proper fix that keeps breakable CUDA graph (BCG) enabled for sparse-DP prefill is deferred.

## Root cause (bisected + devbox-confirmed)

Bisected to #30898 ("Enable breakable prefill CUDA graph for DP attention"): parent `c616d5a55e` is clean, the commit itself reproduces on every trial.

Under this recipe (TP4 / DP4 / DeepEP / DP-attention), a single request leaves the other DP ranks idle. #30898 lets those idle ranks replay the breakable prefill CUDA graph via a fabricated dummy extend. The dummy's hidden states vary run to run and propagate into the real request's logits through the shared EP grouped GEMMs — only at capture buckets 4 and 16, whose grouped-GEMM tiling is composition-sensitive. A determinism hammer on the CI recipe showed ~50% of identical temp-0 request pairs diverging (24/24 distinct logits on fresh prefills at the broken buckets, top-token logprob swinging up to ~1.9 nats); buckets 8/12/20+ are clean, which is why only the ~15-token CI prompt flakes.

## Why disable rather than fix here

Two candidate fixes were prototyped on a 4×B200 devbox against the exact CI recipe:

- **Gate veto** (idle ranks fall back to eager prefill): drives the hammer to 0/6 at every bucket, but it partially reverts #30898 — sparse-DP prefill loses BCG. Rejected as too heavy for a CI-unblock.
- **Deterministic dummy** (point the idle dummy at a reserved, never-written `req_to_token` row so its page mapping is constant): keeps BCG enabled, but **did not** resolve the nondeterminism (still 6/6 at buckets 4/16). So the real source is deeper than the dummy's KV page mapping — likely the captured-metadata refresh (`refresh_for_breakable_cuda_graph_replay_`) or the grouped-GEMM composition on the dummy-extend rank — and needs someone familiar with the DeepEP dummy-extend design.

Given both, disabling the test is the right stopgap; the proper BCG-preserving fix will be a follow-up.

## Change

Skips only `test_determinism_temp_zero` on the BCG class. The other tests in the class (gsm8k accuracy, sanity probes, accept-length) still run. Verified on devbox: `Ran 8 tests ... OK (skipped=1)`.

## Note on test coverage

`test/registered/dp_attn/test_dp_attention_bcg_kl.py` (added by #30898) drives single requests on a dp=2 server and runs with `enable_deterministic_inference=True`; its batch-invariant kernels mask this composition-sensitivity, which is why #30898's own test never caught it. A real regression test for this path wants an all-ranks-busy workload without deterministic-inference mode.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29315537096](https://github.com/sgl-project/sglang/actions/runs/29315537096)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29315536794](https://github.com/sgl-project/sglang/actions/runs/29315536794)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
