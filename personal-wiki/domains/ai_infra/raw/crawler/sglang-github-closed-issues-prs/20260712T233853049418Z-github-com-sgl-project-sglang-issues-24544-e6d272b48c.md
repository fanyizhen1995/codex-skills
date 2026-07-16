---
source_id: sglang-github-closed-issues-prs
title: '[sglang-miles] Integrate PD decode radix cache'
canonical_url: https://github.com/sgl-project/sglang/issues/24544
captured_at: '2026-07-12T23:38:53.049418+00:00'
content_hash: e6d272b48c1819ae56866a09617a35a74b77504cc88adcab4497a5ab78f78bc9
---
# [sglang-miles] Integrate PD decode radix cache

URL: https://github.com/sgl-project/sglang/issues/24544
State: closed
Labels: inactive
Closed at: 2026-07-12T00:35:40Z
Merged at: 

## Motivation

Track integration of decode-side radix cache for PD disaggregation into the `sglang-miles` fork.

This is **especially valuable for long-context multi-turn workloads with high prefix cache hit rates** — e.g. agentic / chat sessions that re-send a large shared system prompt or conversation history each turn. With this feature, the decode worker reuses shared prefixes via a radix tree and only requests the delta KV from prefill instead of re-transferring the full prefix on every turn. The longer the context and the higher the hit rate, the bigger the win (see #19746 benchmarks: ~1.32x request throughput, ~8x p50 TTFT on Qwen3-32B 3P1D with ~91% prefix reuse).

## PRs to integrate

- [ ] #19746 — `[P/D disagg] - support decode side radix cache` (NIXL backend; user-facing flag `--disaggregation-decode-enable-radix-cache`)
- [ ] #24230 — `[pd]: (Bug Fix) Incorrect out_cache_loc slicing in prepare_for_prebuilt` (fixes a slicing bug on top of #19746 when `pre_len > 0`)
- [ ] #24257 — `[PD]: Support incremental transfer for mooncake transfer engine` (extends #19746 to the Mooncake transfer backend; depends on #24230)

Suggested merge order: #19746 → #24230 → #24257.

## Scope / notes

- Decode-side flag: `--disaggregation-decode-enable-radix-cache` (decode worker only).
- After all three PRs land, both `--disaggregation-transfer-backend nixl` and `mooncake` are supported.
- DP attention with this feature is still experimental upstream; good cache hit rates require prefix-aware DP routing.
- Hybrid tree (Mamba/SWA) on the decode side is explicitly out of scope here (called out as a follow-up in #24257).

## Validation plan for sglang-miles

- [ ] Sanity PD disagg run on a small model (e.g. Qwen3-0.6B) with the flag on/off.
- [ ] Accuracy parity (e.g. GSM8K) with the flag on vs. off.
- [ ] Throughput / TTFT benchmark on a long-context, multi-turn, high-cache-hit workload to confirm the upstream win reproduces.
- [ ] Verify both `nixl` and `mooncake` transfer backends.
