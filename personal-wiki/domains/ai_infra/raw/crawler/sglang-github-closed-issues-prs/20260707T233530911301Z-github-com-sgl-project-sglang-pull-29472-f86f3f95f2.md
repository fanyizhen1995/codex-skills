---
source_id: sglang-github-closed-issues-prs
title: '[KDA] Add FlashKDA prefill backend for safe-gate KDA linear attention'
canonical_url: https://github.com/sgl-project/sglang/pull/29472
captured_at: '2026-07-07T23:35:30.911301+00:00'
content_hash: f86f3f95f241908a45fda35ba08b921caa4e7c6d55d043fa435c7d2c755cc027
---
# [KDA] Add FlashKDA prefill backend for safe-gate KDA linear attention

URL: https://github.com/sgl-project/sglang/pull/29472
State: closed
Labels: dependencies, run-ci, run-ci-extra, linear-attention, release-highlight
Closed at: 2026-07-02T03:37:05Z
Merged at: 2026-07-02T03:37:05Z

# [KDA] Add FlashKDA prefill backend for safe-gate KDA linear attention

## Summary

Adds **FlashKDA** (MoonshotAI's fused CUTLASS Kimi Delta Attention kernel) as an optional KDA prefill/extend backend, selectable via `--linear-attn-prefill-backend flashkda`. It replaces the multi-kernel Triton `chunk_kda` prefill path with a single fused kernel that is **1.3–4.6× faster**.

This PR lands the **kernel backend and its dispatch/fallback only** — it is the **prerequisite infrastructure for safe-gate KDA support**. It is opt-in, off by default, depends on an optional package, and transparently falls back to Triton for anything it can't run, so it adds **zero risk** to existing deployments.

## Background: FlashKDA

KDA (Kimi Delta Attention) is the per-channel-gated delta-rule linear attention used by recent KDA models (e.g. Kimi-Linear). The reference prefill (FLA's Triton `chunk_kda`) runs the chunked delta rule as a *sequence* of kernels — `chunk = 64` with intra-chunk rescaling and high-precision accumulation — which is launch- and bandwidth-heavy.

[FlashKDA](https://github.com/MoonshotAI/FlashKDA) (MoonshotAI, open-sourced 2026-04) fuses the whole chunked delta rule into a CUTLASS kernel and trades the rescaling machinery for a numerically tighter design: `chunk = 16`, recurrent state stored in **bf16**, the 16×16 intra-chunk inverse computed in **fp16** via a Neumann series, base-2 `exp`, and tensor-core tiles. The net result is a 1.3–4.6× speedup over the Triton path (cross-validated below on H20 and GB200). Upstream it is wired as FLA's `flashkda` backend, auto-dispatched from `chunk_kda` when its preconditions hold.

## Why the safe gate (the hard precondition)

<img width="2412" height="1770" alt="image" src="https://github.com/user-attachments/assets/1afb016a-9b5e-467b-b3b7-a034c37fa449" />

FlashKDA's speed comes from running the entire chunked recurrence in low precision (bf16 state, fp16 inverse) on small chunks **without rescaling**. That is only numerically valid if the gate's per-step log-decay is **bounded below**. KDA has two gate formulations, chosen at training time:

- **Unbounded (standard):** `a = -exp(A_log)·softplus(g + bias)`, `a ∈ (-∞, 0]`. The cumulative chunk decay `exp(cumsum(a))` can span a huge dynamic range, so the kernel needs larger chunks + careful rescaling — i.e. the Triton path.
- **Safe / bounded:** `a = lower_bound·sigmoid(exp(A_log)·(g + bias))`, `a ∈ (lower_bound, 0)`. With `lower_bound = -5` and `chunk = 16`, `cumsum ∈ [-80, 0]`, so `exp(cumsum)` stays inside bf16's representable range (no rescaling), the 16×16 inverse stays well-conditioned (entries in `[-1,1]`, fp16-safe), and the tensor-core fast path is valid.

```
                  UNBOUNDED (standard)            SAFE / BOUNDED (FlashKDA)
  gate  a   =  −exp(A_log)·softplus(x)        lb·sigmoid(exp(A_log)·x),  lb=−5
  range of a    (−∞ , 0]   no floor               (−5 , 0]   floored
  exp(cumsum)  0 ◄────────► 1  (unbounded)     6.6e−3 ◄─► 1  (≤2 orders, chunk=16)
  bf16 ?        ✗ needs fp32 + rescale            ✓ fits, no rescale
  inverse       ill-conditioned                   |entries|≤1 → fp16 16×16 (Neumann)
  kernel        multi-kernel Triton chunk_kda     ONE fused CUTLASS  →  1.3–4.6×
  memory        can fully forget (0)              retains ≥ e^−5 ≈ 0.67%  (the price)

  why bound ⇒ fast:
      bound a ≥ −5
          ├─► cumsum bounded ─► exp(cumsum) fits bf16 ─► no rescale, bf16 state, chunk=16
          └─► (I+A) well-conditioned (|inv|≤1) ─► fp16 16×16 inverse
                                  │
                                  ▼
                   ONE fused CUTLASS kernel  →  1.3–4.6× vs Triton
```

In short: **bounding the gate trades a sliver of expressiveness (memory can't fully zero out) for the numerical headroom that makes the fused low-precision kernel correct.** It is baked into the checkpoint (safe-gate models init `A_log ≈ 0`; unbounded init `A_log = log(uniform(1,16))`), so it cannot be toggled at inference — a model is one or the other.

## Foundation for safe-gate KDA support (why land it now)

FlashKDA only implements the **safe gate**, so it activates only when a model sets `layer.lower_bound`. Landing the backend first, ahead of and independently of the model-side wiring, means:

- The fast path is reviewed and benchmarked on its own (this PR), keeping the later model PR small.
- Once a safe-gate KDA model threads its bound to `layer.lower_bound` (`kda_safe_gate=true`, `kda_lower_bound=-5`, checkpoint `A_log ≈ 0`) — selecting `--linear-attn-prefill-backend flashkda` turns on the 1.3–4.6× path with **no further kernel work**.
- Until then it is inert (falls back to Triton), so there is no risk to current models.

| model | gate | A_log (checkpoint) | FlashKDA |
|---|---|---|---|
| **FlashKDA target model** | safe (`kda_safe_gate=true`, `lower_bound=-5`) | mean ≈ 0.1, `exp(A_log)∈[0.85,1.47]` | **target — applies once wired** |
| Kimi-Linear-48B-A3B | unbounded | mean ≈ 2.28, `exp(A_log)` up to 201 | falls back to Triton |

## Modifications

- `layers/attention/linear/utils.py` — `LinearAttnKernelBackend.FLASHKDA` + `is_flashkda()`
- `server_args.py` — `flashkda` added to `LINEAR_ATTN_KERNEL_BACKEND_CHOICES`
- `layers/attention/linear/kda_backend.py` — prefill dispatch branch → `FlashKDAKernel`
- `layers/attention/linear/kernels/kda_flashkda.py` — new `FlashKDAKernel` (prefill/extend-only) wrapping `flash_kda.fwd`

## Mechanism

`FlashKDAKernel.extend` passes **raw** tensors plus `A_log`/`dt_bias`/`lower_bound` to `flash_kda.fwd` (the kernel fuses L2-norm / beta-sigmoid / gate internally; beta is inverted to logits since the model already applied sigmoid). The recurrent state layout `[N, H, V, K]` matches the existing KDA pool, so no transpose is needed; the final state is written back in place via `ssm_states[cache_indices]`.

It falls back to Triton `chunk_kda` when:
- `lower_bound is None` (unbounded-gate model), or
- the shortest sequence `< 64` (chunk size), or
- the longest sequence `> 2048` (past the crossover where Triton wins).

`flash_kda` is lazily imported, so the dependency is only needed when the backend is actually selected.

## Correctness

Validated against the production Triton `chunk_kda` on the safe-gate path (bf16, H=32, K=V=128, varlen), inputs cloned per path (`chunk_kda` mutates `g`/`v` in place):

| check | result |
|---|---|
| single-token (hand-verifiable) | bit-close, cos 1.0000, max\|diff\| 3e-4 |
| full-sequence output | cos 0.985 |
| final recurrent state | cos 0.9999 (confirms `[N,H,V,K]` layout) |

Residual is bf16 cross-implementation accumulation (FlashKDA is a different CUTLASS kernel, not bit-exact with Triton — same as FLA's treatment of it).

## Performance (FlashKDA vs Triton `chunk_kda`, raw kernels, fresh clones)

**H20-3e (sm90):**

| B | T | speedup |
|---|---|---|
| 1 | 128 | 5.2× |
| 1 | 512 | 2.2× |
| 1 | 2048 | 1.24× |
| 8 | 512 | 2.0× |
| 16 | 512 | 2.1× |
| 32 | 512 | 2.05× |

**B200 (sm100):**

| B | T | H | speedup |
|---|---|---|---|
| 1 | 128 | 32 | 4.61× |
| 1 | 512 | 32 | 2.60× |
| 1 | 2048 | 32 | 1.27× |
| 16 | 512 | 32 | 2.69× |
| 32 | 512 | 32 | 2.65× |
| 1 | 8192 | 64 | 1.73× |
| 1 | 8192 | 96 | 2.23× |

The B200 `T=8192` results (1.73× / 2.23× at H=64 / 96) match MoonshotAI's published `BENCHMARK_GB200.md` (1.70× / 2.31×), cross-validating the measurement.

## Requirements

- SM90+ GPU and the optional `flash_kda` module installed: `pip install sglang[flashkda]` (or `pip install git+https://github.com/MoonshotAI/FlashKDA.git`).
- bf16, `K == V == 128`, `HV == H` (no GVA), safe gate (`lower_bound` set).
- Prefill/extend only (decode / target-verify fall back).

## Usage

```
--linear-attn-prefill-backend flashkda
```

## Testing

- Kernel correctness vs Triton `chunk_kda` (single-token, full-sequence, final state) on H20-3e and B200.
- Perf benchmarks on H20-3e (sm90) and B200 (sm100), cross-validated against the upstream FlashKDA GB200 benchmark.





























































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28530376386](https://github.com/sgl-project/sglang/actions/runs/28530376386)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28858938282](https://github.com/sgl-project/sglang/actions/runs/28858938282)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
