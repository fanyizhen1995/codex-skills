---
source_id: sglang-github-closed-issues-prs
title: '[Doc] Cookbook: Laguna-XS-2.1 (DFlash low-latency + high-throughput)'
canonical_url: https://github.com/sgl-project/sglang/pull/29884
captured_at: '2026-07-03T02:13:21.700744+00:00'
content_hash: 3b6787d53d14edf8e2035290c0f6227759e726cbb7ae2198c6620ef48cd5195b
---
# [Doc] Cookbook: Laguna-XS-2.1 (DFlash low-latency + high-throughput)

URL: https://github.com/sgl-project/sglang/pull/29884
State: closed
Labels: documentation
Closed at: 2026-07-02T12:05:34Z
Merged at: 2026-07-02T12:05:34Z

## Motivation

Day-0 cookbook page for **poolside/Laguna-XS-2.1** (33B hybrid-SWA MoE, 3B active) in the config-driven format (same design as the Laguna-M.1 page). Companions: #29446 (DFlash support, required for the Low-Latency strategy) and #29761 (INT4 mixed-precision MoE load fix, merged).

## Matrix

| axis | values |
|---|---|
| Hardware | H200, B200, GB300 (single node; tp 8 / 8 / 4) |
| Variant | Default |
| Quantization | BF16, FP8, NVFP4 (Blackwell-only), INT4 |
| Strategy | **Low-Latency** (DFlash, matched-precision draft) / **High-Throughput** (dense) |

Draft and target precision always match (`-DFlash`, `-DFlash-FP8`, `-DFlash-NVFP4`, `-DFlash-INT4`).

## Verification status

- **GB300**: all 8 cells **verified** — full-GSM8K (1319 q, greedy) on 4×GB300 tp 4: dense 75.66 / 71.87 / 78.39 / 66.79 (bf16/fp8/nvfp4/int4), DFlash 76.19 / 72.02 / 74.53 / 67.02 with accept-lengths 3.8–4.2. Spec ≡ dense within noise on every quant.
- **H200 / B200**: commands encode the validated backend rules but are **pending measurement** (bare benchmark stubs, no fabricated numbers) — to be filled in follow-ups.

## Key encoded findings (bisected on GB300)

- **Dense**: leave `--attention-backend` unset — auto-select is correct (fa3 on Hopper, trtllm_mha on Blackwell).
- **DFlash**: auto-select is NOT safe — with speculation active the resolver falls back to flashinfer, which breaks this hybrid-SWA model at tp≥4 (GSM8K 76%→28%). All Low-Latency cells pin the target backend explicitly. Draft worker stays on its automatic fallback (measured ≡ forced fa4).
- `triton` attention is broken for Laguna (GSM8K 13%) — never emitted.
- DFlash cells carry `--mem-fraction-static 0.7` (default fraction OOMs in the draft vocab all-gather at tp 4).

## Checklist

- [x] Config + benchmarks JSX validated (22 cells, full cell↔benchmark parity, draft-precision match)
- [x] docs.json navigation entry
- [ ] H200 / B200 measurements (follow-up)
- [ ] Flip install instructions once #29446 merges

🤖 Generated with [Claude Code](https://claude.com/claude-code)





























































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28581050238](https://github.com/sgl-project/sglang/actions/runs/28581050238)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28581050128](https://github.com/sgl-project/sglang/actions/runs/28581050128)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
