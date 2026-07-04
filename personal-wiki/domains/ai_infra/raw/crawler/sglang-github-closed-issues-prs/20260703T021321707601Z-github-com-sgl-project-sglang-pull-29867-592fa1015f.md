---
source_id: sglang-github-closed-issues-prs
title: 'feat(short-conv): shared ShortConvAttnBackend for ZAYA1 CCA + LFM2 short conv'
canonical_url: https://github.com/sgl-project/sglang/pull/29867
captured_at: '2026-07-03T02:13:21.707601+00:00'
content_hash: 592fa1015f1cd39c29efaf84dc96b048783aa887e5224ebd19826075001d252f
---
# feat(short-conv): shared ShortConvAttnBackend for ZAYA1 CCA + LFM2 short conv

URL: https://github.com/sgl-project/sglang/pull/29867
State: closed
Labels: run-ci, bypass-fastfail
Closed at: 2026-07-02T03:08:00Z
Merged at: 2026-07-02T03:08:00Z

## Summary

Extracts the per-request **conv-state plumbing** shared by hybrid short-conv models into one model-agnostic attention backend, and migrates **ZAYA1 (CCA)** and **LFM2 / LFM2-MoE** onto it. The models no longer touch the pool directly — they receive a `ShortConvMetadata` handle and run their own conv kernel against it.

These models interleave a *causal short conv with per-request conv state* (in the centralized `MambaPool`) with softmax attention:
- **LFM2 / LFM2-MoE** — a depthwise gated short conv (`causal_conv1d`) as a standalone token mixer on its conv layers.
- **ZAYA1** — a two-stage grouped conv plus a one-token `prev_hs` lag, preprocessing q/k for the layer's softmax attention.

They share the state plumbing (per-request slot indices, `has_initial_state`, `query_start_loc`, cuda-graph buffers, once-per-step resolution) but **not** the conv kernel.

## What's in it

- **`ShortConvAttnBackend`** (`layers/attention/linear/short_conv_backend.py`) — owns only the plumbing; hands it out via `conv_state_metadata()` as a `ShortConvMetadata`. Inherits metadata + cuda-graph capture/replay from `MambaAttnBackendBase`. It is a sidecar: invoked directly by the model, never through the full-vs-linear `forward_decode`/`forward_extend` dispatch.
- **`ShortConvHybridAttnBackend`** — wrapper exposing `conv_state_metadata`; softmax layers keep routing through the full-attn backend.
- **`attention_registry`** routes `ZayaConfig` + `Lfm2Config` / `Lfm2MoeConfig` / `Lfm2VlConfig` to the new backend; other mamba2 models keep `Mamba2AttnBackend`.
- Models fetch the handle and run their own conv — **no `get_req_to_token_pool()` access remains in any short-conv model**. ZAYA1's conv kernel (`cca_extend` / `cca_decode`) lives in `zaya.py`.
- `cache_indices` is int64-canonical; the CUDA `causal_conv1d` kernel requires int32, so `causal_conv1d_fn/update` narrow at the kernel boundary (no-op for existing int32 callers).

## Two bugs found by GPU e2e and fixed here

- **LFM2 config import path** — `attn_backend_wrapper` imported `Lfm2MoeConfig`/`Lfm2VlConfig` from the wrong module, crashing scheduler startup for *every* short-conv model. CPU unit tests missed it because the mock backend bypasses the registry.
- **bs>1 cuda-graph decode illegal-memory-access** — the int64 index cache was materialized per conv layer, and a warmup-produced tensor leaked into the captured graph (its producing cast was never recorded) → stale read at replay. Fixed by resolving the indices **once per step in `init_forward_metadata` / `init_forward_metadata_out_graph`** (the decode-graph path refills a persistent int64 buffer in place, so the captured graph reads a stable address); `conv_state_metadata` just returns the cached view.

## Validation (H200, `fa3` + full cuda graph)

- **CPU unit tests**: `test_zaya_cca`, `test_zaya_config`, `test_zaya_mod_tp` pass.
- **LFM2-1.2B**: cuda-graph e2e (generation + 32-example MMLU) passes; decode output **byte-identical** to the pre-refactor baseline.
- **ZAYA1-base**: eager generation + bs=1 cuda-graph generation are coherent.
- **LFM2-MoE**: migrated via the same `Lfm2MoeShortConv` code path; compile/import verified, full e2e not yet run.

## Known pre-existing issue (out of scope)

**ZAYA1 bs>1 cuda-graph decode segfaults** — but the **pre-refactor baseline segfaults identically** at the same point (confirmed by reverting to `cf69f08d2b^` and re-running), so this predates the refactor; ZAYA1's gated e2e was evidently never exercised on this config. LFM2 / LFM2-MoE are unaffected. Tracking separately.

🤖 Generated with [Claude Code](https://claude.com/claude-code)















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28541676121](https://github.com/sgl-project/sglang/actions/runs/28541676121)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28557791724](https://github.com/sgl-project/sglang/actions/runs/28557791724)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
