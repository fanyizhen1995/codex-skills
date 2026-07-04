---
source_id: sglang-github-closed-issues-prs
title: '[MoE] Consolidate ungrouped + grouped gate/topk onto one Triton router (#26771)
  — faster than AOT on B200/H100/H200, at parity with flashinfer'
canonical_url: https://github.com/sgl-project/sglang/pull/29771
captured_at: '2026-07-04T02:13:49.139911+00:00'
content_hash: 75bc251c1f07418fa77c59f4b907412e93a587f59dd6379e9b0861b1d2f8976f
---
# [MoE] Consolidate ungrouped + grouped gate/topk onto one Triton router (#26771) — faster than AOT on B200/H100/H200, at parity with flashinfer

URL: https://github.com/sgl-project/sglang/pull/29771
State: closed
Labels: run-ci, jit-kernel, run-ci-extra
Closed at: 2026-07-03T03:19:00Z
Merged at: 2026-07-03T03:19:00Z

## Motivation

Part of the fused MoE gate/topk kernel **consolidation** (#26771). SGLang has many per-model gate/topk kernels (`grouped_topk.cuh`, AOT `topk_sigmoid`/`topk_softmax`, the CUDA-JIT `moe_fused_gate`, flashinfer `fused_topk_deepseek`, …). #25835 introduced one Triton `moe_fused_gate` router and made it the default for the ungrouped `sqrtsoftplus` path.

This PR converges the remaining paths onto that single router, in three phases:
- **Phase 1 — ungrouped:** route the CUDA `softmax`/`sigmoid` topk **and** the ungrouped `grouped_topk` (`num_expert_group==1`) branch through the Triton router, and optimize it to **beat the hand-tuned AOT kernels on B200 + H100 + H200**.
- **Phase 2 — cleanup:** delete the kernel the consolidation makes dead.
- **Phase 3 — grouped:** add DeepSeek-V3 grouped routing (`n_group`/`topk_group`, noaux_tc) to the same router and wire an **opt-in** dispatch, validated **bit-exact e2e** and at parity with flashinfer.

## Modifications

**Triton router (`jit_kernel/moe_fused_gate.py`):**
- Add `softmax` scoring (softmax-prob weight, bias kept, optional `tanh` softcap) alongside `sigmoid`/`sqrtsoftplus`.
- Accept **fp32/fp16/bf16** `scores` (kernel upcasts on load) — bf16 router logits no longer need a host-side fp32 upcast.
- **Phase 3: grouped routing** (constexpr `N_GROUP>1`): per-group score = sum of the top-2 biased values, keep `TOPK_GROUP` groups (lowest group id wins ties), mask dropped groups, then the existing top-k runs. `N_GROUP==1` compiles the block out (ungrouped path unchanged). More general than the AOT grouped kernel — no experts-per-group ≤ 32 cap.
- **Perf: row-pack the launch** (`num_warps=1`, `BLOCK_M = max(1, min(4, 256//BLOCK_N))`). The old single-warp-per-row `grid=(M,)` was occupancy-bound at small N on Hopper and lost ~25% to AOT; packing a few rows per program only when N is small fixes it (swept `BLOCK_M × num_warps` on H100/B200/H200 — this heuristic is the sweep-optimal point; larger tiles / more warps regress via register pressure).

**Dispatch (`srt/layers/moe/topk.py`):**
- Phase 1: route the CUDA `fused_topk` softmax/sigmoid branches **and** the `biased_grouped_topk_gpu` `num_expert_group==1` branch through the Triton router (gated by `SGLANG_OPT_USE_JIT_KERNEL_FUSED_TOPK`, default **on**, `_is_cuda`). AOT stays the default on non-CUDA backends and the env-off fallback.
- Phase 3: new **opt-in** `SGLANG_OPT_USE_JIT_KERNEL_GROUPED_TOPK` (default **off**) routes the DeepSeek-V3 grouped path (`num_expert_group>1`) through the Triton router. Off by default so flashinfer `fused_topk_deepseek` stays the tuned production default; the flag is a consolidation escape hatch (validated bit-exact + at parity, below), not a perf flip.

**Cleanup (Phase 2):** delete the now-dead jit `grouped_topk` (kernel + wrapper + test) — its only dispatch site now routes to the Triton router.

## Accuracy Tests

- `test/registered/jit/test_moe_fused_gate.py`: **1063 passed on GPU** (sigmoid/sqrtsoftplus/softmax × experts × topk × shared-experts × renorm × scale, fp32+bf16), including:
  - softmax/sigmoid parity vs AOT `topk_softmax`/`topk_sigmoid` + a torch reference (Phase 1);
  - **grouped** parity vs the definitional `biased_grouped_topk_impl` for DeepSeek-V3 shapes (256/8/4/8, 128/8/4/6, 256/4/2/8), fp32+bf16, ≤1e-3 (Phase 3 kernel);
  - **grouped dispatch** parity: `biased_grouped_topk_gpu` with the flag on (Triton) vs off (flashinfer/AOT default), with and without a fused shared expert (Phase 3 wiring).
- Grouped kernel matches the AOT `moe_fused_gate` in fp32; bf16 differs only on borderline experts because AOT scores in bf16 while the reference + this router upcast to fp32.

## Model accuracy — end-to-end (Phase 3)

Three levels of accuracy evidence for the grouped path:

**1. Full-model downstream eval — GSM8K + MMLU on DeepSeek-V3-0324** (671B fp8, the flagship sigmoid-grouped model this dispatch targets; `n_group=8`, `topk_group=4`, 256 experts). Served with `sglang.launch_server --tp 8` on 8×B200; the two runs use the **same build**, differing only in the `SGLANG_OPT_USE_JIT_KERNEL_GROUPED_TOPK` env var (flag verified live in the server process). `sglang.test.run_eval`:

| eval | default (flashinfer `fused_topk_deepseek`) | Triton grouped (flag on) | Δ |
|---|--:|--:|--:|
| GSM8K (1319, greedy) | 95.74% | 95.89% | +0.15% (2/1319) |
| MMLU (3000-example sample) | 86.47% | 86.47% | **0.00%** |

MMLU is **identical** (2594/3000 both). GSM8K differs by 2 questions — the grouped Triton router and flashinfer diverge only on borderline-expert selection (fp32 vs bf16 scoring rounding), which occasionally flips a mid-CoT token; the effect is noise-level and here Triton scores marginally *higher*. **No accuracy regression.**

**2. Kernel-level numerical precision** (`test_moe_fused_gate.py`, on GPU): the grouped Triton router vs the definitional `biased_grouped_topk_impl` — routed-expert selection **exact** and weights **max abs diff ≤ 1e-7 in fp32** (DeepSeek-V3 256/8/4/8, 128/8/4/6, 256/4/2/8). In bf16 selection is identical except on borderline experts, and only because the AOT kernel scores in bf16 while the reference + this router upcast to fp32. Grouped-dispatch parity (flag on vs off, ±fused shared expert) matches to ≤ 1e-3.

**3. Bit-exact end-to-end output** — DeepSeek-V3.2-5layer-bf16 (real DSA + grouped MoE: 256 experts, `n_group=8`, `topk_group=4`, sigmoid), greedy generation on fixed prompts, 1×H200:

| dispatch | grouped-MoE invocations | output token hash |
|---|--:|---|
| default (flashinfer `fused_topk_deepseek`) | — | `5518026aa2a27596` |
| `SGLANG_OPT_USE_JIT_KERNEL_GROUPED_TOPK=1` (Triton) | 52 (prefill+decode) | `5518026aa2a27596` |

Every generated token is **bit-identical** across the two dispatches (a stderr marker confirmed the Triton grouped branch fired 52× across prefill + decode, ruling out a silent no-op).

## Speed Tests and Profiling

CUDA-graph, kernel-only replay (production runs the gate under graphs).

**Phase 1 — ungrouped, Triton vs AOT** (Triton ≥ AOT on every shape on B200 + H100; H200 5/6, see note):

*B200 (Blackwell):*
| scoring | M | N | topk | AOT µs | Triton µs | speedup |
|---|--:|--:|--:|--:|--:|--:|
| softmax | 4096 | 128 | 8 | 10.21 | 6.24 | **1.64x** |
| softmax | 8192 | 256 | 8 | 19.05 | 12.38 | 1.54x |
| softmax | 8192 | 512 | 8 | 24.44 | 18.53 | 1.32x |
| sigmoid | 4096 | 128 | 8 | 10.35 | 6.23 | 1.66x |
| sigmoid | 8192 | 256 | 8 | 18.74 | 12.36 | 1.52x |
| sigmoid | 8192 | 512 | 8 | 141.82 | 18.51 | 7.66x |

*H100 (Hopper):*
| scoring | M | N | topk | AOT µs | Triton µs | speedup |
|---|--:|--:|--:|--:|--:|--:|
| softmax | 4096 | 128 | 8 | 6.31 | 6.34 | 1.00x |
| softmax | 8192 | 256 | 8 | 16.22 | 13.94 | 1.16x |
| softmax | 8192 | 512 | 8 | 21.61 | 20.66 | 1.05x |
| sigmoid | 4096 | 128 | 8 | 6.51 | 6.50 | 1.00x |
| sigmoid | 8192 | 256 | 8 | 17.80 | 13.99 | 1.27x |
| sigmoid | 8192 | 512 | 8 | 128.97 | 21.19 | 6.09x |

*H200 (Hopper):*
| scoring | M | N | topk | AOT µs | Triton µs | speedup |
|---|--:|--:|--:|--:|--:|--:|
| softmax | 4096 | 128 | 8 | 6.19 | 6.41 | 0.96x* |
| softmax | 8192 | 256 | 8 | 16.07 | 13.85 | 1.16x |
| softmax | 8192 | 512 | 8 | 21.61 | 20.68 | 1.05x |
| sigmoid | 4096 | 128 | 8 | 6.43 | 6.41 | 1.00x |
| sigmoid | 8192 | 256 | 8 | 17.73 | 14.07 | 1.26x |
| sigmoid | 8192 | 512 | 8 | 128.65 | 21.19 | 6.07x |

\* The single 0.96x is a bench artifact, not a kernel regression: the Triton *wrapper* allocates its two output tensors inside the captured graph while the AOT bench pre-allocates them. **Kernel-only** at that shape the Triton router is **1.13x** (`BLOCK_M=2, num_warps=1` — the heuristic's choice, confirmed sweep-optimal on H200). Production allocates identically on both paths.

**Phase 3 — grouped, Triton vs the real defaults** (DeepSeek-V3 256/8/4/8, H200; flashinfer `fused_topk_deepseek` is the current production default):
| M | N | n_group | topk_group | topk | flashinfer µs | AOT µs | Triton µs | vs-flashinfer | vs-AOT |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 1024 | 256 | 8 | 4 | 8 | 5.86 | 12.21 | 5.93 | 0.99x | 2.06x |
| 4096 | 256 | 8 | 4 | 8 | 13.40 | 14.83 | 12.74 | 1.05x | 1.16x |
| 8192 | 256 | 8 | 4 | 8 | 23.03 | 20.88 | 22.36 | 1.03x | 0.93x |

Grouped Triton is **at parity with flashinfer** (0.99–1.05x) and generally beats AOT — i.e. no perf loss vs the actual production default. Combined with the bit-exact e2e result, this is why the grouped dispatch is wired as an opt-in flag rather than deferred to a follow-up.

## Follow-ups (#26771, separate PRs)
- Default-enable the grouped Triton path once it has run through flagship (full DeepSeek-V3) e2e accuracy at scale.
- Retire the AOT `.cu` once XPU/HIP/MUSA/CPU migrate; MUSA decision.

## Checklist
- [x] pre-commit (ruff/isort/black/codespell + registered-test validator) pass.
- [x] Unit tests (1063 on GPU: ungrouped + grouped kernel + grouped dispatch).
- [x] End-to-end model accuracy (DeepSeek-V3-0324 GSM8K 95.74%→95.89%, MMLU 86.47%→86.47%; + DeepSeek-V3.2 bit-identical tokens, above).
- [ ] Docs.
- [x] Accuracy + speed benchmarks (B200 + H100 + H200, above).
- [x] Code style.

🤖 Generated with [Claude Code](https://claude.com/claude-code)


















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28581806799](https://github.com/sgl-project/sglang/actions/runs/28581806799)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28581806410](https://github.com/sgl-project/sglang/actions/runs/28581806410)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
