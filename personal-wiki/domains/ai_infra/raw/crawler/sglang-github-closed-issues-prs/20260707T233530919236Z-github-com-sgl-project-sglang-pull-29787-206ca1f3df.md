---
source_id: sglang-github-closed-issues-prs
title: '[Spec] Anchor GLM-5.2 MTP IndexShare topk on the draft-extend step'
canonical_url: https://github.com/sgl-project/sglang/pull/29787
captured_at: '2026-07-07T23:35:30.919236+00:00'
content_hash: 206ca1f3df4e21e5284efa61ef40f1572834d3c0c28adc32c2e7d85d35d9af96
---
# [Spec] Anchor GLM-5.2 MTP IndexShare topk on the draft-extend step

URL: https://github.com/sgl-project/sglang/pull/29787
State: closed
Labels: deepseek, speculative-decoding, run-ci, run-ci-extra
Closed at: 2026-07-07T03:36:49Z
Merged at: 2026-07-07T03:36:49Z

## Summary

Successor of https://github.com/sgl-project/sglang/pull/29654, move the topk capture to draft extend phase. Discuss with @zRzRzRzRzRzRzR offline and we believe this conceptually aligned with GLM 5.2 behaviour

GLM-5.2's MTP (NextN) draft reuses the DSA indexer top-k across draft-decode steps (`index_share_for_mtp_iteration`) rather than recomputing it each step. Currently the reused top-k is captured on the **first draft-decode step**, whose query hidden state is the draft model's own step-0 output. That anchor is one step too late — the IndexShare seed should come from the **last verified token's (target-derived) hidden state produced during draft-extend**.

This PR captures the indexer top-k during **draft-extend** (gathering the last position per request) and threads that seed through:
- the draft-decode loop (`eagle_worker_v2.py`, `deepseek_nextn.py`),
- the draft / draft-extend **CUDA-graph** capture+replay static buffers,
- `EagleDraftInput.filter_batch` / `merge_batch`,
- the overlap-schedule `FutureMap` relay (so the seed survives batching / async overlap).

Gated by `seed_topk_from_extend`, which is active **only** when `index_share_for_mtp_iteration` is on and the model exposes `index_topk`. Non-DSA / non-MTP paths are untouched (short-context DSA-dense requests are unaffected).

## Benchmark — accept length, before vs after

`nvidia/GLM-5.2-NVFP4`, TP4, EAGLE `steps=5 / topk=1 / draft=6`, `temp=0` greedy, natural EOS, `kv-cache-dtype=fp8_e4m3`, hierarchical cache on. Metric = server-side `generation_tokens_total / spec_verify_calls_total` from `/metrics`. **before** = current `main` (step-0 anchor, post #29654); **after** = this PR. 3 replicates/arm, cache flushed per dataset.

| dataset | out_len | before | after | Δ |
|---|---:|---:|---:|---:|
| mtbench | 771 | 3.631 | 3.663 | +0.032 |
| humaneval | 688 | 4.305 | 4.333 | +0.027 |
| gsm8k | 717 | 4.489 | 4.490 | +0.002 |
| math500 | 1630 | 4.599 | 4.610 | +0.010 |
| aime | 3899 | 4.635 | 4.634 | −0.000 |
| openhands_longctx | 503 | 5.115 | 5.177 | +0.061 |

Notes:
- The short-prompt/short-output DSA-dense sets (mtbench/humaneval/gsm8k) are where this mechanism is inactive; their deltas are within noise. The intended effect is the long-context sparse regime (`openhands_longctx` +0.061; larger as context grows).
- For the record: a prior cross-framework "≈0.6 higher accept" observation on OpenHands turned out to be a **degenerate-output artifact** (target+draft drift into repeated tokens, trivially inflating accept). It is not used as a target here.

## Test plan

- [ ] `index_share_for_mtp_iteration` on, long-context GLM-5.2 run — accept length matches the numbers above; outputs bit-identical to `main` at `temp=0` (only verify-call count moves).
- [ ] CUDA-graph decode + draft-extend graph paths exercised (`--cuda-graph-max-bs-decode`), incl. batch grow/shrink (filter/merge) and overlap schedule.
- [ ] Non-DSA model / MTP off — no behavior change (seed path gated off).
- [ ] CI `_DEBUG_ASSERT` (SGLANG_IS_IN_CI) passes with the new pool-indexed `dsa_topk_indices` buffer.

Draft: seeking review on the approach + the buffer/relay plumbing before finalizing.























































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28751939780](https://github.com/sgl-project/sglang/actions/runs/28751939780)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28751939750](https://github.com/sgl-project/sglang/actions/runs/28751939750)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
