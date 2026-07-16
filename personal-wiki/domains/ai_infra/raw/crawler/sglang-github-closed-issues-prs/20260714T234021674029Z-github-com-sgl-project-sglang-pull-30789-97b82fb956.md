---
source_id: sglang-github-closed-issues-prs
title: '[Kernel] Migrate generic attention kernels to sglang.kernels (RFC #29630,
  Phase 2.5, 4/7)'
canonical_url: https://github.com/sgl-project/sglang/pull/30789
captured_at: '2026-07-14T23:40:21.674029+00:00'
content_hash: 97b82fb95650ede0167b53be63a9da3ff597df0eb8c857eea8a51c55b9bef0f4
---
# [Kernel] Migrate generic attention kernels to sglang.kernels (RFC #29630, Phase 2.5, 4/7)

URL: https://github.com/sgl-project/sglang/pull/30789
State: closed
Labels: deepseek, blackwell, run-ci, bypass-fastfail
Closed at: 2026-07-14T08:53:46Z
Merged at: 2026-07-14T08:53:46Z

## Motivation

Phase 2.5 sweep **4 of 7** (migration plan in RFC #29630): the generic attention-family Triton kernels.

## Modifications

**Wholesale moves** (byte-identical; imports rewritten repo-wide):

| From | To | Kernels |
|---|---|---|
| `srt/layers/attention/utils.py` | `ops/attention/utils.py` | 8 (MLA fp8 quantize+rope, reshape_and_cache variants, shuffle gather) |
| `srt/layers/attention/flash_mla_sm120.py` + `_triton.py` | `ops/attention/` | 2 |
| `srt/layers/attention/nsa/triton_decode/` (whole package) | `ops/attention/nsa_triton_decode/` | 8 |
| `srt/layers/dcp/kernels.py` | `ops/attention/dcp_kernels.py` | 4 + `CPTritonContext` |

**Extraction**: `flashattention_backend.py`'s embedded `_build_pa_page_table` kernel + launcher → `ops/attention/pa_page_table.py`; the backend no longer imports triton at all.

Registered migrated entry points as `KernelSpec` inventory.

## Verification

- Import-purity intact; `test_kernels_namespace.py` + `test_fused_op.py`: 33 passed.
- Attention backends exercise these kernels through the rewritten imports in their existing CI lanes (FA3/FlashMLA/NSA/DCP).

Part of the Phase 2.5 series: #30784 (1/7), #30786 (2/7), #30787 (3/7). Independent — any merge order.

🤖 Generated with [Claude Code](https://claude.com/claude-code)







































## Kernel-migration verification (no perf / config regression)

All 7 moved attention kernels are byte-identical relocations (git rename **R100** for 5; the 2 non-R100 deltas are **import-path-only**, no kernel-logic change) — `dcp_kernels`, `flash_mla_sm120`(`_triton`), the `nsa_triton_decode` set, `attention/utils`. No tuning configs moved; no `__file__`-relative config lookup in moved kernels → no config regression.

**Empirical cross-migration A/B (H200):** representative kernels across the Phase-2.5 series were benchmarked main-vs-PR with zero regression — block-fp8 GEMM (#30784, config-backed), MoE router (#30786), fused dual-residual RMSNorm (#30787), DSA `act_quant` (#30792). Because every kernel in this PR is a byte-identical / import-only relocation, per-kernel latency is invariant by construction. The direct attention kernels (flash-MLA / NSA decode) require live KV-cache metadata, so their standalone A/B is covered by the byte-identity guarantee rather than a synthetic microbench.























































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29298657543](https://github.com/sgl-project/sglang/actions/runs/29298657543)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29298657419](https://github.com/sgl-project/sglang/actions/runs/29298657419)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
