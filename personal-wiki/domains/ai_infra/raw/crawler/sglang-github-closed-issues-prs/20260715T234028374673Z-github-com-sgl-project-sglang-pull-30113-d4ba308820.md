---
source_id: sglang-github-closed-issues-prs
title: '[KDA] Add FlashInfer SM100 KDA decode + MTP (target_verify) backend'
canonical_url: https://github.com/sgl-project/sglang/pull/30113
captured_at: '2026-07-15T23:40:28.374673+00:00'
content_hash: d4ba30882004a4aa16b9ee4a6d16dfe7bc402c6abeb4ea6a12d6b1d7bd348c61
---
# [KDA] Add FlashInfer SM100 KDA decode + MTP (target_verify) backend

URL: https://github.com/sgl-project/sglang/pull/30113
State: closed
Labels: speculative-decoding, run-ci, flashinfer, run-ci-extra, linear-attention
Closed at: 2026-07-15T07:04:20Z
Merged at: 2026-07-15T07:04:20Z

## Summary

This PR adds a FlashInfer (Blackwell / SM100) backend for **KDA** (Kimi Delta Attention) linear attention, providing both single-token **decode** and the first numerically-correct **MTP / speculative-decode `target_verify`** (topk=1) path for KDA — which KDA previously lacked entirely. Enable with `--linear-attn-decode-backend flashinfer` (SM100, requires `--mamba-ssm-dtype bfloat16`).

## Motivation

KDA had no `target_verify` path, so KDA models (e.g. Kimi-Linear, ling-v3) could not use speculative decoding (EAGLE / MTP / n-gram) at all. GDN already has the full decode + prefill + MTP story (including a FlashInfer backend); this PR brings KDA to parity for decode + MTP on Blackwell by wrapping FlashInfer's `recurrent_kda` (the single KDA op that covers both standard decode and fused spec-decode). Prefill stays on Triton / CuTe DSL — FlashInfer has no KDA chunk-prefill kernel.

## Modifications

- **`kernels/kda_flashinfer.py`** (new): `FlashInferKDAKernel(LinearAttnKernelBase)` wrapping `flashinfer.kda_decode.recurrent_kda`. Implements `decode` (in-place pool update) and `target_verify` (topk=1). Lazy import + SM100 guard; `extend` raises (no FlashInfer KDA prefill).
- **`kda_backend.py`**: `KDAKernelDispatcher` gains an `is_flashinfer()` decode branch and a `target_verify()` method; `KDAAttnBackend` gains `verify_intermediate_state_indices` and a `forward_extend` → `_forward_target_verify` path (conv1d MTP with intermediate-window checkpointing + the central post-verify rollback), mirroring the GDN backend. **KDA MTP is dispatched to FlashInfer only** (see correctness note below); Triton / CuTe DSL decode backends leave `verify_kernel = None` and `target_verify()` raises a clear error.
- **`kernels/kda_triton.py`**: `TritonKDAKernel.target_verify` (via `fused_sigmoid_gating_delta_rule_update(is_kda=True, disable_state_update=True, ...)`). Its per-draft-token attention output is correct and is used as the unit-test reference, but its end-to-end rollback checkpointing is not yet correct for KDA, so it is **not** wired into production (see limitations).
- **`mem_cache/memory_pool.py`**: `conv_window_dedup_enabled` gains an `is_kda` guard — KDA keeps the dense conv-window layout (required; see below).
- **`test/registered/attention/test_kda_decode_flashinfer.py`** (new): 11 unit tests — FlashInfer `decode` and `target_verify` match the Triton reference per-token across batch/spec shapes; **`target_verify`'s per-step checkpoint states match a sequential-decode reference** (the correctness property the central MTP rollback depends on — an output-only check misses it, which is exactly how the Triton verify's e2e bug hides); plus a tree-spec-rejection guard.
- **`benchmark/bench_linear_attention/bench_kda_flashinfer_mtp.py`** (new): FlashInfer-vs-Triton decode + verify correctness and per-call latency.

`LinearAttnKernelBackend.FLASHINFER` / the `"flashinfer"` CLI choice already existed — no `utils.py` / `server_args.py` changes needed.

## Key contract details

- **Gate**: KDA decode/verify use the softplus gate `g = -exp(A_log) * softplus(a + dt_bias)`, so the wrapper calls `recurrent_kda(..., use_gate_in_kernel=True)` to match the Triton reference exactly.
- **Beta**: the model passes a beta *logit* (Triton applies `sigmoid` in-kernel); `recurrent_kda` wants pre-sigmoid beta, so the wrapper passes `sigmoid(b)`.
- **State layout**: SSM state is `[N, HV, V, K]` everywhere (committed pool, speculative `intermediate_ssm`, and `recurrent_kda`), so no transpose is needed on the SSM side.
- **MTP adapter**: `recurrent_kda` writes each draft token's post-state into pool slots given by `ssm_state_indices`; the wrapper points those at the speculative `intermediate_ssm` scratch (slot = `request*T + step`) and seeds column 0 with the committed state, so the existing central rollback (`update_mamba_state_after_mtp_verify`) commits the accepted-length state unchanged.

## Correctness: conv-window layout must stay dense for KDA

KDA's conv-state pool is physically `[pool, width, dim]`, so the KDA backend `.transpose(-1, -2)`s the conv-window before the conv kernel (GDN's native layout is `[.., dim, width]`). The sliding-window conv-intermediate has a deduplicated layout — an **overlapping `as_strided` view** that halves the footprint by aliasing physical columns across consecutive draft steps. That overlap is only idempotent when the window is written raw (as GDN does); it does **not** survive KDA's transpose (the per-draft-token windows land in the wrong physical columns → corrupt committed conv state → coherent first token then degenerate output). Fix: `conv_window_dedup_enabled(..., is_kda)` keeps KDA on the **dense** conv-window layout. Confirmed on Kimi-Linear MTP: dedup conv → garbage (gsm8k 0.03); dense conv + FlashInfer verify → gsm8k 0.895, matching the 0.90 non-spec reference.

## Validation (B200, SM100, Kimi-Linear-48B-A3B-Instruct, TP2)

**Unit (kernel-level).** `test_kda_decode_flashinfer` — FlashInfer `decode` and `target_verify` match the Triton reference per-token across batch sizes and spec lengths, **and `target_verify`'s per-step checkpoint states (what the rollback commits on accept) match a sequential-decode reference** (11/11 pass on B200; output tol ~5e-2, state `[V,K]` layout confirmed).

**End-to-end (gsm8k, 200 questions, 5-shot, n-gram speculative decode).** n-gram is used because Kimi-Linear has no MTP head (`num_nextn_predict_layers=0`), so it exercises `target_verify` without a draft model. Same model / questions / dense conv for all rows:

| config | decode | verify | Accuracy | Invalid |
|---|---|---|---|---|
| non-spec reference | flashinfer | — | 0.900 | 0.000 |
| **MTP (this PR)** | **flashinfer** | **flashinfer** | **0.895** | **0.000** |

## Performance

- **Decode** (`recurrent_kda` in-kernel `cu_seqlens` path; CUDA-graph, pure GPU): FlashInfer wins at large batch and is at parity/slower at small batch — B=1 0.67x, B=64 0.93x, B=128 ~1.0x (parity), **B=256 1.35x (FlashInfer faster)**. ncu (B=64) puts the `recurrent_kda` decode kernel at **29.6 us** vs Triton `fused_sigmoid_gating_delta_rule_update` **36.8 us**.
- **MTP throughput** is workload-dependent via the accept rate. On gsm8k + n-gram the accept rate is low (accept_len ~1.5), so MTP output throughput (~625 tok/s) is ≈ non-spec (~667 tok/s) — MTP pays off on more repetitive / structured workloads with higher accept rates, not on gsm8k. This PR's headline is **correctness** (first correct KDA MTP) plus the decode-kernel win; it does **not** claim an MTP speedup on gsm8k.

### Microbenchmark (`bench_kda_flashinfer_mtp.py`, B200, bf16, K=V=128, H=HV=16)

Full output of the eager per-call microbench (CUDA-event wall time, warmup 20 / iters 100):

```
KDA decode (T=1): FlashInfer (SM100) vs Triton
     B |  triton(us) | flashinfer(us) | speedup | out_max_diff
     1 |        68.4 |          73.7  |  0.93x  |   3.05e-05
     4 |        67.2 |          73.7  |  0.91x  |   6.10e-05
    16 |        66.3 |          73.2  |  0.91x  |   6.10e-05
    32 |        67.4 |          73.1  |  0.92x  |   1.22e-04
    64 |        65.8 |          74.2  |  0.89x  |   1.22e-04
   128 |        66.9 |          73.7  |  0.91x  |   1.22e-04

KDA target_verify (MTP, T=8): FlashInfer (SM100) vs Triton
  B(xT)|  triton(us) | flashinfer(us) | speedup | out_max_diff
     1 |        69.2 |         128.6  |  0.54x  |   6.10e-05
     4 |        69.5 |         127.1  |  0.55x  |   1.22e-04
    16 |        70.4 |         127.7  |  0.55x  |   2.44e-04
    32 |        69.6 |         132.2  |  0.53x  |   2.44e-04
    64 |       112.2 |         189.5  |  0.59x  |   2.44e-04
   128 |       195.8 |         331.3  |  0.59x  |   1.22e-04
```

## How to enable

```bash
python3 -m sglang.launch_server \
    --model-path <kimi_linear-or-other-KDA-model> \
    --tp 2 --trust-remote-code \
    --mamba-ssm-dtype bfloat16 \
    --linear-attn-decode-backend flashinfer \
    --speculative-algorithm NGRAM \
    --speculative-num-draft-tokens 8 \
    --speculative-ngram-min-bfs-breadth 1 --speculative-ngram-max-bfs-breadth 1
```

Prefill stays on Triton. KDA MTP requires the FlashInfer decode backend (SM100); other decode backends raise a clear error if speculative decode is enabled.

## Testing

- `python -m pytest test/registered/attention/test_kda_decode_flashinfer.py` (SM100 + `recurrent_kda`-capable FlashInfer required; skipped otherwise).
- `python benchmark/bench_linear_attention/bench_kda_flashinfer_mtp.py` — FlashInfer-vs-Triton decode + verify correctness and latency (use CUDA-graph / ncu, not eager wall-clock which is CPU-dispatch-bound).

















































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29301333959](https://github.com/sgl-project/sglang/actions/runs/29301333959)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:hourglass_flowing_sand: [Run #29301333846](https://github.com/sgl-project/sglang/actions/runs/29301333846)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
