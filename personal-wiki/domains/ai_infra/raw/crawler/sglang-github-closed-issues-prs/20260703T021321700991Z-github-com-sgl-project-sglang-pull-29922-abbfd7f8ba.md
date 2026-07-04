---
source_id: sglang-github-closed-issues-prs
title: '[MoE] Add DeepSeek-V3 grouped routing to the unified Triton router (stacked
  on #29771)'
canonical_url: https://github.com/sgl-project/sglang/pull/29922
captured_at: '2026-07-03T02:13:21.700991+00:00'
content_hash: abbfd7f8ba7d733aa5c7c7d9f09b262fd18be79f8362e95eed80b88480fa8b73
---
# [MoE] Add DeepSeek-V3 grouped routing to the unified Triton router (stacked on #29771)

URL: https://github.com/sgl-project/sglang/pull/29922
State: closed
Labels: jit-kernel
Closed at: 2026-07-02T11:52:59Z
Merged at: 

> **Draft / stacked on #29771.** This branch is based on #29771 (the ungrouped consolidation), so the diff currently includes its commits. The **grouped delta is the single commit `b6858dcb60`**. Rebase to a clean diff once #29771 merges. Do not merge before #29771.

## Motivation
Continues the MoE gate/topk consolidation (#26771): add DeepSeek-V3-style **grouped** routing to the same Triton `moe_fused_gate` router introduced in #25835 and extended for softmax/sigmoid in #29771, so one kernel covers ungrouped **and** grouped top-k.

## Modifications
Grouped branch in `_router_triton_kernel`, constexpr-gated by `N_GROUP > 1` (ungrouped path unchanged): per-group score = sum of the top-2 biased values → keep `TOPK_GROUP` groups (lowest group id wins ties) → mask dropped groups' experts → existing top-k. Weight stays the bias-free activated score. More general than the AOT grouped kernel (no `experts_per_group ≤ 32` cap). New `num_expert_group`/`topk_group` args on the `moe_fused_gate` wrapper.

**Dispatch is NOT changed** — DeepSeek-V3 still uses the AOT/flashinfer grouped path. This PR only adds the capability; see the gate below.

## Accuracy Tests
`test_moe_fused_gate.py::test_moe_fused_gate_grouped_matches_production_impl` — grouped parity vs `biased_grouped_topk_impl` (fp32+bf16, incl. DeepSeek-V3 256/8/4/8), **passes on B200 at ≤1e-7**. Matches the AOT grouped `moe_fused_gate` in fp32.

## Speed Tests
CUDA-graph kernel-only vs the AOT grouped kernel on B200 (DeepSeek-V3 shapes): **1.22–1.75x** (M4096 1.73x, M8192 1.22x, M8192+shared 1.75x).

## Gate before default-enabling (not in this PR)
In **bf16**, the grouped Triton selects slightly different *borderline* experts than the AOT (the AOT scores in bf16; the reference + this kernel upcast to fp32). Switching DeepSeek-V3's dispatch therefore needs **on-model e2e accuracy validation** (GSM8K/MMLU, Triton-grouped vs AOT-grouped) first. H200 numbers are also TODO (no H200 was reachable when benched).

## Checklist
- [x] pre-commit clean
- [x] Unit test (grouped parity, B200)
- [ ] Docs
- [x] Speed benchmark (B200; H200 pending hardware)
- [x] Code style

🤖 Generated with [Claude Code](https://claude.com/claude-code)







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28579167137](https://github.com/sgl-project/sglang/actions/runs/28579167137)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28579166988](https://github.com/sgl-project/sglang/actions/runs/28579166988)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
