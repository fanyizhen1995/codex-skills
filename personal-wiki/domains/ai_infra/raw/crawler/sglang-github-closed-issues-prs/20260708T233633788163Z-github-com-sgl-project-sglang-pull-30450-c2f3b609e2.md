---
source_id: sglang-github-closed-issues-prs
title: Fix FlashInfer A2A IMA by DP-synchronizing the decode graph bucket (#30242)
canonical_url: https://github.com/sgl-project/sglang/pull/30450
captured_at: '2026-07-08T23:36:33.788163+00:00'
content_hash: c2f3b609e28759f894f42ed6d46b21da6220409f9f2292c98fd51a6acf9e13fc
---
# Fix FlashInfer A2A IMA by DP-synchronizing the decode graph bucket (#30242)

URL: https://github.com/sgl-project/sglang/pull/30450
State: closed
Labels: run-ci
Closed at: 2026-07-08T21:34:50Z
Merged at: 2026-07-08T21:34:50Z

## Motivation

Fixes #30242 — CUDA illegal-memory-access on **DeepSeek-V4 NVFP4 disaggregated decode** (GB300, TP/DP/EP=16, `moe-a2a-backend=flashinfer`). Bisected by the reporter to #29461.

### Root cause

With FlashInfer MoE A2A + DP attention, `require_mlp_tp_gather` is `False` (standard DeepSeek config: `moe_dense_tp_size=1` + `enable_dp_lm_head`). So each rank picks its decode CUDA-graph bucket from its **local** batch size. Different DP/EP ranks then replay **different-sized graphs** and pass different `runtime_max_tokens_per_rank` into `MoeAlltoAll`'s fixed-geometry `[ep_size, runtime_max_tokens_per_rank, ...]` buffers → geometry mismatch → IMA (surfacing later at the sampler's `argmax`).

#29461 routed graph *capture* to `x.shape[0]` (baked per-graph), which is exactly the value that diverges across ranks once they replay different buckets.

## Fix

Make `require_mlp_tp_gather` return `True` for FlashInfer A2A (one line in `require_mlp_tp_gather`). This reuses the existing DP-synchronized machinery so:

- the decode graph runner sizes the cuda-graph bucket from the **cross-rank max** (`max(global_num_tokens_cpu)`), so every EP rank replays the **same** bucket;
- the dispatcher's `max(dp_global)` path is used for DP attention in **eager, capture, and replay** — a rank-invariant value that tracks the actual batch instead of the static workspace capacity (memory-efficient, unlike the pre-#29461 static cap).

No literal MLP TP-gather is introduced: the MoE layer stays `SCATTERED` (gated on `get_moe_a2a_backend()`), and the a2a op still owns dispatch/combine. This covers eager, capture/replay, prefill, and speculative decoding via the already-tested `require_mlp_tp_gather=True` path. See #30242 (comment) for the same suggestion from @trevor-m.

### Dispatcher cleanup (`flashinfer.py`)

`runtime_max_tokens_per_rank` now has two rank-invariant cases (the wasteful static-capacity middle branch is dropped):

- **Case 1 — `max(dp_global)`**: DP attention feeding EP (per-rank token counts differ → take the cross-rank max).
- **Case 2 — `x.shape[0]`**: **SP attention feeding EP** (tokens are sequence-parallel scattered uniformly → `x.shape[0]` is already identical on every EP rank), a single EP rank, or capture of those. This preserves the SP+EP layout.

Two asserts make the invariants explicit and fail fast (they run in Python during eager and capture; replay reuses the baked value):
1. DP attention must not reach the `x.shape[0]` branch with `ep_size > 1` (catches the #30242 pattern and the unsupported `SGLANG_SCHEDULER_SKIP_ALL_GATHER`);
2. the chosen `runtime_max_tokens_per_rank` must cover this rank's own tokens.

Also see #30432 for the (now more) misleading `require_mlp_tp_gather` name.

## Test Plan / Validation needed

I could not reproduce on the target multi-node GB300 hardware; the change compiles and passes pre-commit. Please validate:

- [ ] The #30242 repro (DeepSeek-V4 NVFP4, TP/DP/EP=16, disagg decode) — no IMA, correct decode output.
- [ ] A `require_mlp_tp_gather=True` DP-attention run (ensure the shared bucket-selection path is unaffected).
- [ ] The **SP attention → EP** FlashInfer A2A layout (confirm it still takes Case 2 / `x.shape[0]`).
- [ ] Speculative decoding + FlashInfer A2A (goes through the `require_mlp_tp_gather=True` path).

## Related

- Regression from #29461
- Naming follow-up: #30432























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28926384044](https://github.com/sgl-project/sglang/actions/runs/28926384044)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28926383999](https://github.com/sgl-project/sglang/actions/runs/28926383999)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
