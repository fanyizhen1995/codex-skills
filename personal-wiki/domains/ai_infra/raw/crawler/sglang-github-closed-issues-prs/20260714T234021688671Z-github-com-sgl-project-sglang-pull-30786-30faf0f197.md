---
source_id: sglang-github-closed-issues-prs
title: '[Kernel] Migrate scattered MoE kernels to sglang.kernels (RFC #29630, Phase
  2.5, 2/7)'
canonical_url: https://github.com/sgl-project/sglang/pull/30786
captured_at: '2026-07-14T23:40:21.688671+00:00'
content_hash: 30faf0f1970b2e68ca9eece4db658e165dc6019e626f5961afe2835538de007b
---
# [Kernel] Migrate scattered MoE kernels to sglang.kernels (RFC #29630, Phase 2.5, 2/7)

URL: https://github.com/sgl-project/sglang/pull/30786
State: closed
Labels: quant, amd, lora, sgl-kernel, run-ci, jit-kernel, bypass-fastfail
Closed at: 2026-07-14T01:03:22Z
Merged at: 2026-07-14T01:03:22Z

## Motivation

Phase 2.5 sweep **2 of 7** (see the updated migration plan in RFC #29630): move the ~42 Triton MoE kernels still living under `srt/layers/moe` into `sglang.kernels.ops.moe`.

## Modifications

**Wholesale moves** (byte-identical, `git diff -M` shows 100% renames; imports rewritten repo-wide):

| From (srt/layers/moe) | To (sglang/kernels/ops/moe) | Kernels |
|---|---|---|
| `ep_moe/kernels.py` | `ep_moe_kernels.py` | 22 Triton |
| `moe_runner/triton_utils/fused_moe_triton_kernels.py` | `fused_moe_triton_kernels.py` | 10 Triton |
| `moe_runner/triton_utils/mxfp8_moe_amd_gfx95.py` | `mxfp8_moe_amd_gfx95.py` | 2 Triton |
| `rocm_moe_utils.py` | `rocm_moe_utils.py` | 2 Triton + aiter wrappers |
| `router.py` | `router.py` | 2 Triton + thin launcher |

**Extractions from mixed modules** (kernel code verbatim; policy/glue stays in srt):

- `topk.py`: the `_fill_padded_rows` kernel block had accumulated **two near-identical copies** (an assert-based one and a later raise-based one; the later definition wins at runtime). Both are removed and the runtime-winning copy becomes `ops/moe/fill_padded_rows.py`.
- `deepep_waterfill.py`: the two dispatch kernels, `WaterfillDispatchPlan`, and `materialize_waterfill_dispatch_fused` move to `ops/moe/deepep_waterfill_kernels.py`; `DeepEPWaterfillBalancer` (policy) and `expand_topk_with_shared_expert` (torch.compile eager path) stay in srt and import the moved names.

Also registered the migrated public entry points as `KernelSpec` inventory (TRITON backend).

## Verification

- `import sglang.kernels` stays metadata-only (import-purity intact).
- `test_kernels_namespace.py` + `test_fused_op.py`: 33 passed.
- MoE correctness/e2e coverage runs unchanged in its existing CI lanes through the rewritten imports.

## Notes

Merge order within the series: after #30784 (1/7) — both touch `ops/moe/__init__.py` (append-append) and `fp8_kernel`'s lazy import; I'll rebase this branch once 1/7 lands.

🤖 Generated with [Claude Code](https://claude.com/claude-code)















































## Kernel-migration verification (no perf / config regression)

All 5 moved MoE kernels are **byte-identical relocations (git rename R100)** — `ep_moe_kernels`, `fused_moe_triton_kernels`, `mxfp8_moe_amd_gfx95`, `rocm_moe_utils`, `router` — only their import paths changed, so per-kernel latency is unchanged by construction. No tuning-config files were moved, and no moved kernel uses a `__file__`-relative config lookup, so there is no config-reachability regression.

**Empirical A/B (H200, `fused_moe_router_shim`, hidden=4096, experts=8, topk=2, bf16):**

| batch | main µs | PR µs | Δ |
|--:|--:|--:|--:|
| 512 | 30.16 | 30.45 | +1.0% |
| 4096 | 29.83 | 29.23 | −2.0% |

→ within run-to-run noise; no latency regression.

























































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29297131002](https://github.com/sgl-project/sglang/actions/runs/29297131002)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29297130868](https://github.com/sgl-project/sglang/actions/runs/29297130868)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
