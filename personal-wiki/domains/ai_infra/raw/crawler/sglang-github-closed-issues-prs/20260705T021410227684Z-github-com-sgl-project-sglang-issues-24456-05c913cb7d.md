---
source_id: sglang-github-closed-issues-prs
title: '[R3] Long collectives with --enable-return-routed-experts on Kimi K2 EP=DP=TP=32'
canonical_url: https://github.com/sgl-project/sglang/issues/24456
captured_at: '2026-07-05T02:14:10.227684+00:00'
content_hash: 05c913cb7d779b5d4a4145f950833854a4f69c23a130d3385f6e9694de8ec740
---
# [R3] Long collectives with --enable-return-routed-experts on Kimi K2 EP=DP=TP=32

URL: https://github.com/sgl-project/sglang/issues/24456
State: closed
Labels: inactive
Closed at: 2026-07-05T00:41:38Z
Merged at: 

## Summary

With `--enable-return-routed-experts` on Kimi K2 (EP=DP=TP=32), profiles show frequent "long collectives" during decode — DeepEP dispatch/combine kernels that appear to take much longer than usual. Investigation suggests these are not actually slow collectives, but rather **late-entering ranks**: a single DP rank stalls on the scheduler main thread while serializing routed-experts output, and all 32 ranks block at the next collective waiting for it.

## Setup

- Model: Kimi K2 Thinking (FP8)
- Parallelism: TP=32, DP=32, EP=32, 4 nodes
- Per-DP-rank batch size: 8 (global batch ≈ 256)
- Input length ~30,000, output length ~200
- DeepEP a2a backend, normal mode
- `--enable-return-routed-experts`

## Analysis

### 1. Finishes happen on almost every step

With output length ~200, each request finishes with probability `1/200` per decode step:

- Per DP rank (bs=8): `p(≥1 finish/step) = 1 − (199/200)^8 ≈ 3.9%`, expected `0.04` finishes/step.
- Across 32 DP ranks: `p(any rank has a finish/step) = 1 − (1 − 0.039)^32 ≈ 73%`, expected `~1.28` finishes/step globally.

So in steady state ~3 out of 4 decode steps have at least one DP rank retiring a request somewhere.

### 2. Each finish stalls that rank's scheduler thread

Synchronously, on the scheduler main thread, when a request finishes with `--enable-return-routed-experts`:

- `get_routed_experts` — GPU sync + scattered pinned-CPU gather of ~77 MB (40k × 60 × 8 × int32) per long request.
- `stream_output_generation` → `send_pyobj` to the detokenizer — pickles a `torch.Tensor` via `torch.serialization._legacy_save` (~200–500 MB/s) + zmq IPC.

Per long finished request this is ~300–600 ms of stall on the scheduler main thread. K2 decode step is ~30–80 ms, so each finish costs ~5–15 decode steps of stall on that one rank.

### 3. One stalled rank stalls all 32

All DP ranks rendezvous at the next collective (DeepEP dispatch/combine). The slowest scheduler dictates when the collective can begin: while one rank is pickling `routed_experts`, the other 31 are blocked inside the collective. In the trace this shows up as a **"long collective"** — but it's really a late-entering rank.

## Traces

**Diagram 1 — Without `--enable-return-routed-experts` (R3 disabled):** decode steps are uniform, no long collective bubbles.

![diagram-1-no-r3](https://raw.githubusercontent.com/ByronHsu/sglang/issue-assets/issue-assets/24456-1.png)

**Diagram 2 — With `--enable-return-routed-experts` (R3 enabled):** large bubbles appear in the NCCL/DeepEP rows, lining up with finished requests on individual ranks.

![diagram-2-r3](https://raw.githubusercontent.com/ByronHsu/sglang/issue-assets/issue-assets/24456-2.png)

**Diagram 3 — Scheduler-thread view of the bubble:** the offending rank shows `get_routed_experts` → `stream_output_generation` → `send_pyobj` (`torch.serialization._legacy_save` → `zmq socket.send`) running on the main thread, exactly during the "long collective" on the other ranks.

![diagram-3-router-bubble](https://raw.githubusercontent.com/ByronHsu/sglang/issue-assets/issue-assets/24456-3.png)

## Hypothesis / Asks

1. Confirm the diagnosis: is `get_routed_experts` + tensor pickling expected to run synchronously on the scheduler main thread for every finished request?
2. Can routed-experts gather/serialization be moved off the hot path — e.g. to a worker thread, or batched/asynchronous detokenizer send — so a single finishing request on one DP rank doesn't stall the global collective for 5–15 decode steps?
3. Is there a cheaper transport than `torch.serialization._legacy_save` + zmq for this tensor (e.g. raw bytes, shared memory, or skipping pickling)?

This is fairly visible at scale (DP=32, long out len → finishes are basically continuous globally), so the effective decode throughput regression from `--enable-return-routed-experts` is much larger than the per-request work would suggest.
