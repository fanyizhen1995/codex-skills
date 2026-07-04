---
source_id: sglang-github-closed-issues-prs
title: '[CP] Consolidate decode-context-parallel (DCP) helpers into layers/dcp/'
canonical_url: https://github.com/sgl-project/sglang/pull/29365
captured_at: '2026-07-04T02:13:49.131360+00:00'
content_hash: e8763a3cd39a85d359b49e7fdc45ac4bb23fb4beaedb9a43d7b9af84d5327e16
---
# [CP] Consolidate decode-context-parallel (DCP) helpers into layers/dcp/

URL: https://github.com/sgl-project/sglang/pull/29365
State: closed
Labels: deepseek, run-ci
Closed at: 2026-07-03T19:25:40Z
Merged at: 2026-07-03T19:25:40Z

> **Draft / WIP — Phase 1 of a 3-phase effort.** Behavior-preserving consolidation (no logic change). Phases 2–3 (below) add the decode-CP strategy and wire the backends.

## Motivation

Two decode-context-parallel (DCP) implementations landed on `main` a day apart:

- **#25090** — Qwen3.5 / Triton / MHA-GQA / AMD-HIP
- **#14194** — DeepSeek-V2/V3.1 / FlashInfer-MLA + FlashMLA / CUDA

They cover disjoint model/backend/platform combos but **duplicate several DCP primitives across two separate homes** — including an identically-named `cp_lse_ag_out_rs` defined twice. This PR consolidates them into a single **`layers/dcp/`** subpackage.

> **Location note (review feedback):** an earlier revision nested this under the CP-v2 strategy package (`layers/cp/dcp/`). Decode-CP and prefill-CP are **orthogonal axes** (separate `_DCP` vs `attn_cp` process groups; decode vs prefill phase), and the package has **zero code dependency** on `layers/cp/`, so it now lives at the top level **`layers/dcp/`** (a sibling of `layers/cp/`). Because `layers/` is a namespace package, this also removes the `layers.cp ↔ mem_cache` import cycle the nested version had to work around — **this PR touches zero files under `layers/cp/`.**

## Structure: before → after (this PR)

**Before** — DCP scattered across two independently-added homes:

```
layers/attention/utils.py          # #25090 (Triton/MHA): get_dcp_lens,
                                    #   create_triton_kv_indices_for_dcp_triton, cp_lse_ag_out_rs
layers/attention/triton_backend.py # _dcp_lens, _dcp_kv_indices, _forward_extend_dcp
layers/utils/dcp_utils.py          # #14194 (MLA, ~724 lines): accessors, cp_lse_ag_out_rs
                                    #   (a 2nd, same-named fn!), create_dcp_kv_indices, metadata,
                                    #   planner, all-gather helpers, Triton LSE-merge
mem_cache/{memory_pool,triton_ops/mla_buffer}.py  # masked / set_mla KV-write kernels
```

**After** — one top-level `layers/dcp/` subpackage:

```
layers/dcp/
  __init__.py   # public surface — only the 15 symbols imported outside the subpackage
  metadata.py   # DecodeContextParallelMetadata
  kernels.py    # all @triton.jit DCP kernels + correct_attn_out / CPTritonContext
  comm.py       # group accessors, dcp_enabled, all-gather helpers,
                #   cp_lse_ag_out_rs_mha (torch / all-reduce) + cp_lse_ag_out_rs_mla (Triton / reduce-scatter)
  layout.py     # get_dcp_lens, filter_dcp_local_kv_indices, update_local_kv_lens_for_dcp
  planner.py    # prepare_decode_context_parallel_metadata, plan_dcp_decode_metadata
```

Key moves:
- the two same-named `cp_lse_ag_out_rs` are disambiguated → **`_mha`** / **`_mla`**;
- `layers/utils/dcp_utils.py` is **deleted** and the DCP block removed from `layers/attention/utils.py` — all importers now import directly from `layers.dcp`;
- backend-specific KV-write kernels stay in their `mem_cache` homes (justified divergence: separate K/V vs fused MLA latent), dispatched by backend.

## What's in this PR (behavior-preserving)

1. **Relocate** the DCP primitives into `layers/dcp/` (`metadata`/`kernels`/`comm`/`layout`/`planner`).
2. **Collapse** `update_local_kv_lens_for_dcp` into `get_dcp_lens` (bit-identical); drop the pure-alias `get_attention_dcp_group`.
3. **Extract** the shared `_ag_lse` all-gather-LSE prologue used by both LSE-merge variants.
4. **De-duplicate the two `cp_lse_ag_out_rs`** into `_mha` (torch/all-reduce) and `_mla` (Triton/reduce-scatter), keeping both backend-forced bodies verbatim.
5. **Delete `dcp_utils.py`** and the `attention/utils.py` DCP block; retarget every importer to `layers.dcp`.
6. Curate `dcp/__init__` `__all__` to the 15 externally-imported symbols; document that `DecodeContextParallelMetadata` is intentionally standalone (re-parent decision deferred to P2).

Relocated bodies are **bit-identical to base** (AST-verified); the only arithmetic change is the `get_dcp_lens`/`update_local_kv_lens_for_dcp` collapse, which is proven bit-identical and pinned by `test/registered/dcp/test_dcp_layout_unit.py`.

## Validation

Behavior-preserving, verified on B200 (DeepSeek-V2-Lite-Chat, tp2, FlashInfer-MLA, CUDA), both via a `PYTHONPATH` checkout **and** an installed editable build of the branch:
- **Import smoke**: `layers.dcp` resolves, all rewired importers load, **no import cycle** (server boots with `dcp_size=2` where the nested version previously risked one).
- **GSM8K parity**: dcp2 `0.650`/`0.655` vs dcp1 `~0.655` — within run-to-run noise, no regression.
- **Unit sweep (8/8 pass)**: `test_dcp_layout_unit` (moved to `test/registered/dcp/`), `test_cp_strategy_unit` (prefill CP-v2 intact), `test_reduce_scatter_along_dim`, `test_create_kvindices`, `test_set_mla_kv_buffer`, and the three rewired backends `mla_flashinfer`/`mla_flashmla`/`mla_triton`.
- No test references the removed/renamed DCP API; the `check-registered-tests` registry hook and lint pass.

## Roadmap

- **Phase 1 — this PR.** Relocate + de-duplicate. No logic change.
- **Phase 2 — decode strategy.** Add a decode contract to the CP-v2 `ContextParallelStrategy` ABC (default `NotImplementedError`, so prefill strategies are untouched) + `DecodeContextParallelStrategy(InterleaveCPStrategy)` bound to the `_DCP` group (DCP's `pos % N == rank` owner rule *is* the interleave layout). The strategy *imports* from `layers/cp/` but the package stays at `layers/dcp/` — placement and the strategy relationship are independent.
- **Phase 3 — wire backends.** Route the Triton/MHA and FlashInfer-MLA / FlashMLA decode paths through `get_decode_cp_strategy()`, removing the remaining direct calls; then propose the decode contract upstream to #27252.

### Target structure (end state, after Phase 3)

```
layers/
  cp/          # prefill CP-v2 strategy package (base ABC + zigzag/interleave) — unchanged home
  dcp/
    strategy.py  # DecodeContextParallelStrategy(InterleaveCPStrategy) — owns the _DCP group,
                 #   the single entry point backends call; imports the ABC/parent from layers/cp/
    metadata.py · kernels.py · comm.py · layout.py · planner.py   # internals, driven by the strategy
```

End state: backends (`triton_backend`, `flashinfer_mla_backend`, `flashmla_backend`, the deepseek forward methods) call `get_decode_cp_strategy().<op>()` instead of importing DCP free functions directly — decode-CP becomes a first-class CP-v2 strategy on the `_DCP` axis, while living in its own top-level package.

## Checklist

- [ ] CI green — existing DCP/CP tests (`test/registered/dcp/*`, `test/registered/cp/*`, `test/registered/amd/test_qwen3p5_triton_dcp.py`) pass unchanged.
- [ ] Maintainer review of the `layers/dcp/` module layout.

🤖 Generated with [Claude Code](https://claude.com/claude-code)















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28643382217](https://github.com/sgl-project/sglang/actions/runs/28643382217)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28679680212](https://github.com/sgl-project/sglang/actions/runs/28679680212)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
