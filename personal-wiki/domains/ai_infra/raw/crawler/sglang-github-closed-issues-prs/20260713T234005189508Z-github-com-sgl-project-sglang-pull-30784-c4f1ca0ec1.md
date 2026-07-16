---
source_id: sglang-github-closed-issues-prs
title: '[Kernel] Migrate scattered quantization kernels to sglang.kernels (RFC #29630,
  Phase 2.5, 1/7)'
canonical_url: https://github.com/sgl-project/sglang/pull/30784
captured_at: '2026-07-13T23:40:05.189508+00:00'
content_hash: c4f1ca0ec1ab18a8eff26bdf6e13b5cf64d86c099b3459e6b6678635fa5fb852
---
# [Kernel] Migrate scattered quantization kernels to sglang.kernels (RFC #29630, Phase 2.5, 1/7)

URL: https://github.com/sgl-project/sglang/pull/30784
State: closed
Labels: documentation, quant, amd, lora, deepseek, sgl-kernel, blackwell, run-ci, diffusion, jit-kernel, bypass-fastfail
Closed at: 2026-07-13T08:17:01Z
Merged at: 2026-07-13T08:17:01Z

## Motivation

Phase 2.5 of RFC #29630 (see the updated migration plan in the issue): a full-tree audit after #30044 found ~280 Triton kernels plus CuTe DSL / TileLang kernels still scattered outside the three canonical locations. This is sweep **1 of 7**: the quantization group.

## Modifications

Byte-identical file moves + import rewrites only (`git diff -M` shows 100% renames):

| From (srt/layers/quantization) | To | Kernels |
|---|---|---|
| `fp8_kernel.py` | `sglang/kernels/ops/quantization/fp8_kernel.py` | 12 Triton |
| `int8_kernel.py` | `sglang/kernels/ops/quantization/int8_kernel.py` | 3 Triton |
| `awq/awq_triton.py` | `sglang/kernels/ops/quantization/awq_triton.py` | 2 Triton |
| `mxfp8_amd_gfx95.py` | `sglang/kernels/ops/quantization/mxfp8_amd_gfx95.py` | 2 Triton |
| `nvfp4_gemm_swiglu_nvfp4_quant.py` | `sglang/kernels/ops/quantization/nvfp4_gemm_swiglu_nvfp4_quant.py` | CuTe DSL (SM100) |
| `configs/` (159 w8a8 tuned JSONs) | `sglang/kernels/ops/quantization/configs/` | used only by fp8/int8_kernel |

`mxfp4_flashinfer_trtllm_moe.py` is a quant-method module with one embedded kernel: `PackTopkIds` + its Triton kernel are extracted verbatim into `sglang/kernels/ops/moe/pack_topk_ids.py` (MoE-routing functionality, also consumed by `moe_runner/flashinfer_trtllm.py`); the quant-method glue stays in srt.

Also:
- Registered all migrated public entry points as `KernelSpec` inventory (TRITON / CUTE_DSL backends).
- Rewrote all in-tree importers (82 files across `python/`, `test/`, `benchmark/`).
- The only content change inside a moved file is `fp8_kernel`'s lazy sibling import of `int8_kernel`.
- Extended `test_kernels_namespace.py` expected-ops set.

## Verification

- `import sglang.kernels` stays metadata-only (import-purity test passes: no `sgl_kernel` / `sglang.jit_kernel` import).
- Registry check: 24 quantization/moe ops registered with correct backends.
- `test_kernels_namespace.py` + `test_fused_op.py`: 33 passed.
- Existing quant correctness tests (`test/registered/quant/*`) now import through the new path and run unchanged in their CI lanes.

## Checklist

Part of the RFC #29630 Phase 2.5 series (1/7). Next: moe, top-level layers strays, generic attention, dsa+dsv4, linear-attention family, vendored fla/mamba.

🤖 Generated with [Claude Code](https://claude.com/claude-code)












































## Kernel-migration verification (no perf / config regression)

All moved modules are byte-identical relocations (git rename similarity **R100**, except `fp8_kernel.py` at **R099** whose only delta is an `int8_kernel` import-path rewrite — no kernel logic changed), so per-kernel latency is unchanged by construction.

Import fixes in this PR: `awq/__init__` and `fp8_utils` still imported `awq_triton` / `fp8_kernel` / `mxfp8_amd_gfx95` from pre-migration paths → repointed to `sglang.kernels.ops.quantization.*`.

| moved kernel | rename | note |
|---|---|---|
| awq_triton | R100 | identical |
| fp8_kernel | R099 | only int8_kernel import path changed |
| int8_kernel | R100 | identical |
| mxfp8_amd_gfx95 | R100 | identical |
| nvfp4_gemm_swiglu_nvfp4_quant | R100 | identical |

**Tuning configs:** 158 fp8/int8 block-shape config JSONs moved together with `get_w8a8_block_fp8_configs`; the loader resolves them via `os.path.dirname(__file__)/configs`, so co-locating loader + configs preserves the lookup.

**Empirical A/B (H200, `w8a8_block_fp8_matmul`, N=1536 K=7168, block=[128,128], fp16 out):** both main and PR load the tuned config (`CONFIG_HIT=True`, 18 entries) and latency matches within noise:

| M | main µs | PR µs | Δ |
|--:|--:|--:|--:|
| 64 | 41.85 | 42.04 | +0.5% |
| 512 | 40.29 | 40.59 | +0.7% |
| 4096 | 118.71 | 118.59 | −0.1% |

→ tuning config still hit at the new location, no latency regression.





























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29226631377](https://github.com/sgl-project/sglang/actions/runs/29226631377)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29226631233](https://github.com/sgl-project/sglang/actions/runs/29226631233)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
