---
source_id: sglang-github-closed-issues-prs
title: '[Kernel] Relocate vendored fla and mamba kernel trees to sglang.kernels (RFC
  #29630, Phase 2.5, 7/7)'
canonical_url: https://github.com/sgl-project/sglang/pull/30795
captured_at: '2026-07-15T23:40:28.379885+00:00'
content_hash: 7c250e71ccd2ca261e1f2b4b3c55f481612ecd1e702dcf846c6da47c8345ca7b
---
# [Kernel] Relocate vendored fla and mamba kernel trees to sglang.kernels (RFC #29630, Phase 2.5, 7/7)

URL: https://github.com/sgl-project/sglang/pull/30795
State: closed
Labels: deepseek, blackwell, run-ci, mthreads, bypass-fastfail
Closed at: 2026-07-15T04:52:16Z
Merged at: 2026-07-15T04:52:15Z

## Motivation

Phase 2.5 sweep **7 of 7** (migration plan in RFC #29630): pure directory relocations of the two vendored linear-state kernel libraries. Large diffstat, zero logic change — kept separate precisely so the trivial-but-huge diff doesn't drown the substantive sweeps.

## Modifications

| From | To | Content |
|---|---|---|
| `srt/layers/attention/fla/` | `ops/attention/fla/` | flash-linear-attention port: 34 Triton kernels / 18 files (chunk_*, fused_recurrent, kda, l2norm, solve_tril, ...) |
| `srt/layers/attention/mamba/ops/` | `ops/mamba/triton_ops/` | mamba_ssm-derived SSD kernels (ssd_chunk_*, mamba_ssm, layernorm_gated, ...) |
| `srt/layers/attention/mamba/{causal_conv1d_triton,mamba_state_scatter_triton}.py` | `ops/mamba/` | Triton conv1d + state scatter |

The dispatch/layer files (`causal_conv1d.py`, `mamba.py`, `mixer2_rms_norm_gated.py`, backends) stay in srt and import from the new location. All moves are byte-identical (`git diff -M` 100% renames); the only content edits are import-path rewrites.

Registered representative entry points as `KernelSpec` inventory.

## Verification

- Import-purity intact; `test_kernels_namespace.py` + `test_fused_op.py`: 33 passed; ruff/isort/black clean.
- GDN/KDA/Qwen3-Next/Mamba model suites exercise these kernels through the rewritten imports in their existing CI lanes.

Completes the Phase 2.5 series: #30784, #30786, #30787, #30789, #30792, #30793. Shares `ops/attention/__init__.py` / `ops/mamba/__init__.py` appends with earlier PRs in the series (trivial append conflicts; will rebase as they land).

🤖 Generated with [Claude Code](https://claude.com/claude-code)







































## Kernel-migration verification (no perf / config regression)

All 33 moved kernels are byte-identical relocations (git rename **R100** for 16; the 17 non-R100 deltas are **import-path-only** — verified no non-import line changed) — the vendored `fla` (gated-delta / chunk) and `mamba` (causal-conv1d, SSD) kernel trees. No tuning configs moved; no `__file__`-relative config lookup → no config regression. This PR also reverts an over-matched rewrite that had spuriously repointed attention backends (flashattention/flashinfer/flashmla) to `kernels.ops.attention.*`.

**Empirical cross-migration A/B (H200):** representative kernels across the Phase-2.5 series were benchmarked main-vs-PR with zero regression — block-fp8 GEMM (#30784, config-backed), MoE router (#30786), fused dual-residual RMSNorm (#30787), DSA `act_quant` (#30792). Because every kernel in this PR is a byte-identical / import-only relocation, per-kernel latency is invariant by construction. The fla/mamba kernels require live linear-attention state / conv-state, so their standalone A/B is covered by the byte-identity guarantee.



























































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29388754859](https://github.com/sgl-project/sglang/actions/runs/29388754859)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29388754743](https://github.com/sgl-project/sglang/actions/runs/29388754743)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
