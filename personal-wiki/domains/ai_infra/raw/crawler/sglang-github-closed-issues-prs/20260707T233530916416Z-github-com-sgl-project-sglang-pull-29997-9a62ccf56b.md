---
source_id: sglang-github-closed-issues-prs
title: '[MoE] Retire the AOT moe_fused_gate / kimi_k2_moe_fused_gate gate kernels
  (#26771)'
canonical_url: https://github.com/sgl-project/sglang/pull/29997
captured_at: '2026-07-07T23:35:30.916416+00:00'
content_hash: 9a62ccf56b18d698d14ec6b8a32dfe414da39a73ea3e2e6a3b3250d7cb76da94
---
# [MoE] Retire the AOT moe_fused_gate / kimi_k2_moe_fused_gate gate kernels (#26771)

URL: https://github.com/sgl-project/sglang/pull/29997
State: closed
Labels: deepseek, sgl-kernel, run-ci, mthreads, jit-kernel, run-ci-extra
Closed at: 2026-07-07T05:53:18Z
Merged at: 2026-07-07T05:53:18Z

## Motivation

Follow-up to the MoE gate/topk **consolidation** (#26771), on top of the now-merged #29771. With #29771 the unified Triton router covers every CUDA gate/topk path (ungrouped softmax/sigmoid/sqrtsoftplus + DeepSeek-V3 grouped). This PR retires the two AOT gate kernels that are now redundant on CUDA, converging toward the issue's goal of one Triton + one CUDA (JIT `moe_fused_gate.cuh`) gate kernel.

## Modifications

**(1) `moe_fused_gate` (`csrc/moe/moe_fused_gate.cu`)** — its only live CUDA caller was the grouped `experts_per_group <= 32` fallback in `biased_grouped_topk_gpu`. Rerouted that fallback to the Triton router (no MAX_VPT=32 cap, handles any experts-per-group). flashinfer `fused_topk_deepseek` stays the grouped default; the Triton router is the fallback (and the opt-in force via `SGLANG_OPT_USE_JIT_KERNEL_GROUPED_TOPK`).

**(2) `kimi_k2_moe_fused_gate` (`csrc/moe/kimi_k2_moe_fused_gate.cu`)** — already dead on #29771: Phase 1 routes the 384/256-expert single-group sigmoid path (Kimi-K2, MiMo-V2 Flash) through the Triton router; only a `register_fake` stub remained. Removed. The experimental-LoRA bf16 fast path uses a *separate* JIT kernel (`trtllm_lora_temp`), untouched.

**Removed** (both ops, all backends): the 3 `.cu` (incl. the MUSA `moe_fused_gate_musa.cu` — sglang's MUSA path uses the external `mate` package, not this sgl_kernel op, so **no runtime impact**), their CUDA + MUSA pybind registrations, header decls, `CMakeLists.txt`/`setup_musa.py` build entries, the sgl_kernel Python wrappers + `__all__` exports, and the corresponding unit tests + benchmarks. **ROCm never registered these ops → unaffected.** Net **−2454 lines**.

## Accuracy / correctness

Dispatch smoke on 1×H200 (`biased_grouped_topk_gpu` vs the definitional `biased_grouped_topk_impl`, bf16 inputs), with flashinfer **forced off** so grouped routing exercises the new Triton fallback:

| case | path exercised | max abs diff |
|---|---|--:|
| grouped DeepSeek-V3 256/8/4 k8 | Triton fallback (was AOT moe_fused_gate) | 2.98e-08 |
| grouped 128/8/4 k6 | Triton fallback | 2.98e-08 |
| Kimi-K2 384/1/1 k8 | Triton router | 2.98e-08 |
| MiMo-V2 256/1/1 k8 | Triton router | 2.98e-08 |

4/4 pass. The behavioral change (grouped fallback → Triton) matches the reference; the Kimi/MiMo routing was already the #29771 default. The existing `test_moe_fused_gate.py` suite (grouped kernel + dispatch parity) continues to cover the router itself.

## Build

sgl-kernel rebuilt from source on CUDA (sm90, H200): **compiles + links cleanly** (`pip install` exit 0, "Successfully installed"). Symbol check on the freshly-built `common_ops.abi3.so`: `moe_fused_gate` → **0 symbols**, `kimi_k2_moe_fused_gate` → **0**, kept `moe_sum`/`topk_softmax` → present — confirming the pybind + CMake removals are complete and nothing else referenced the retired ops. The sgl-kernel CI build lane also gates this.

## Checklist
- [x] Dispatch correctness (4/4 vs reference, above).
- [x] sgl-kernel local rebuild — compiles + links; retired symbols confirmed dropped.
- [x] Rebased onto `main` (#29771 merged) — single-commit diff.

🤖 Generated with [Claude Code](https://claude.com/claude-code)













































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28712190880](https://github.com/sgl-project/sglang/actions/runs/28712190880)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28712190791](https://github.com/sgl-project/sglang/actions/runs/28712190791)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
