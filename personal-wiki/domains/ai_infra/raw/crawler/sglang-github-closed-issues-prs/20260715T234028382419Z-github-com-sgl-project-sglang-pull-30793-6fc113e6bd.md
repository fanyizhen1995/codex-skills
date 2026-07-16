---
source_id: sglang-github-closed-issues-prs
title: '[Kernel] Migrate linear-attention, MiniMax-sparse and diffusion kernels to
  sglang.kernels (RFC #29630, Phase 2.5, 6/7)'
canonical_url: https://github.com/sgl-project/sglang/pull/30793
captured_at: '2026-07-15T23:40:28.382419+00:00'
content_hash: 6fc113e6bd682b009d5d7c8e3c16dbc22e6f1466c8b2257fc17b8a3539c5def1
---
# [Kernel] Migrate linear-attention, MiniMax-sparse and diffusion kernels to sglang.kernels (RFC #29630, Phase 2.5, 6/7)

URL: https://github.com/sgl-project/sglang/pull/30793
State: closed
Labels: run-ci, diffusion, bypass-fastfail
Closed at: 2026-07-15T03:21:36Z
Merged at: 2026-07-15T03:21:36Z

## Motivation

Phase 2.5 sweep **6 of 7** (migration plan in RFC #29630): the linear-attention family, MiniMax sparse ops, and the `multimodal_gen` strays — including the only `.cu` source living outside the canonical kernel trees.

## Modifications

**Wholesale moves** (byte-identical; imports rewritten repo-wide):

| From | To |
|---|---|
| `attention/linear/{seg_la,lightning_attn}.py` (12 Triton) | `ops/attention/linear/` |
| `attention/linear/kernels/{gdn_blackwell,kda_blackwell}/` (CuTe DSL) | `ops/attention/linear/` — now co-located with the same-family `jit_kernel/cutedsl_gdn/kda` per the namespace plan; the thin dispatch wrappers in `linear/kernels/` stay in srt |
| `attention/minimax_sparse_ops/{common,decode,prefill}/` (12 Triton) | `ops/attention/minimax_sparse/` — `msa`/`naive`/backend logic stays in srt |
| `multimodal_gen/csrc/render/` (hunyuan3d rasterizer `.cu` + mesh_processor cpp_extension loaders) | `ops/diffusion/render/` |

**Extraction**: `multimodal_gen` `sparse_linear_attn.py`'s `get_block_map`/`mean_pool`/`compress_kernel`/`_attn_fwd` → `ops/diffusion/sparse_linear_attn_kernels.py`; the `SparseLinearAttentionBackend` class stays.

Registered migrated entry points as `KernelSpec` inventory.

## Verification

- Import-purity intact; `test_kernels_namespace.py` + `test_fused_op.py`: 33 passed; all changed files py_compile + ruff clean.
- GDN/KDA/MiniMax/diffusion suites exercise these kernels through the rewritten imports in their existing CI lanes.

Part of the Phase 2.5 series: #30784, #30786, #30787, #30789, #30792. Shares `ops/attention/__init__.py` appends with 3-5/7 (trivial append conflicts; will rebase as they land).

🤖 Generated with [Claude Code](https://claude.com/claude-code)







































## Kernel-migration verification (no perf / config regression)

All 20 moved kernels are byte-identical relocations (git rename **R100** for 18; the 2 non-R100 deltas are **import-path-only**) — linear-attention (`lightning_attn`, `gdn_blackwell`, `kda_blackwell`), MiniMax-sparse attention, and diffusion kernels. No tuning configs moved; no `__file__`-relative config lookup → no config regression.

**Empirical cross-migration A/B (H200):** representative kernels across the Phase-2.5 series were benchmarked main-vs-PR with zero regression — block-fp8 GEMM (#30784, config-backed), MoE router (#30786), fused dual-residual RMSNorm (#30787), DSA `act_quant` (#30792). Because every kernel in this PR is a byte-identical / import-only relocation, per-kernel latency is invariant by construction. For `lightning_attention`, a synthetic microbench reproduces **identical** runtime behavior on main and PR (same code path); `gdn/kda_blackwell` are SM100/Blackwell-only (not exercised on H200).





































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29386035710](https://github.com/sgl-project/sglang/actions/runs/29386035710)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29386035275](https://github.com/sgl-project/sglang/actions/runs/29386035275)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
