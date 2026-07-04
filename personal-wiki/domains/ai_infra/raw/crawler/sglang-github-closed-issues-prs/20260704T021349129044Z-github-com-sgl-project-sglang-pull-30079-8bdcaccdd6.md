---
source_id: sglang-github-closed-issues-prs
title: '[MoE] Fix moe_fused_gate out-of-range expert id on all-NaN rows (fixes eagle_dp_attention
  crash)'
canonical_url: https://github.com/sgl-project/sglang/pull/30079
captured_at: '2026-07-04T02:13:49.129044+00:00'
content_hash: 8bdcaccdd637c8226b65f18543d5258ec1a8cee04a0ecd105ea8c2f9882c6465
---
# [MoE] Fix moe_fused_gate out-of-range expert id on all-NaN rows (fixes eagle_dp_attention crash)

URL: https://github.com/sgl-project/sglang/pull/30079
State: closed
Labels: jit-kernel
Closed at: 2026-07-04T01:48:52Z
Merged at: 2026-07-04T01:48:52Z

## Problem

`test/registered/spec/eagle/test_eagle_dp_attention.py` (`TestEAGLE3EngineDPAttention`) crashes the server during decode CUDA-graph capture in the scheduled full run, with a `CUDBG_EXCEPTION_WARP_ILLEGAL_ADDRESS` in `count_and_sort_expert_tokens_kernel` (the `moe_align_block_size` sort).

## Root cause

PR #29771 (issue #26771) made the unified Triton router the default for ungrouped softmax/sigmoid MoE (`SGLANG_OPT_USE_JIT_KERNEL_FUSED_TOPK=True`), so qwen3-moe now routes topk through `moe_fused_gate` instead of the AOT `topk_softmax` kernel.

On an **all-NaN gating row** — produced for garbage padding positions during EAGLE3 + DP-attention graph capture — `max_val` is NaN, so `cur == max_val` is false on every lane and the top-k tie-break `tl.min(lane_id)` falls through to the `N + 1` sentinel. That out-of-range expert id (129 for 128 experts) makes `moe_align` index `cumsum_buffer[topk_id + 1]` = 130 into a size-`num_experts + 2` (130) buffer → out-of-bounds → the illegal address. The old AOT kernel tolerated NaN rows, so this was latent until the routing was flipped.

## Fix

Map `NaN -> -inf` before the top-k ranking so degenerate rows still select in-range experts (matching the AOT kernel). Finite values and `-inf` are untouched, so normal rows are bit-identical.

## Verification (standalone, H200)

- All-NaN / Inf gating rows now stay within `[0, num_experts-1]` (were emitting 129).
- The full `moe_fused_gate -> moe_align_block_size` pipeline no longer faults on all-NaN input.
- Broad correctness sweep (many token counts, seeds, dtypes) unchanged; top-k selection matches a torch reference.
- CUDA-graph capture + replay of the router→align pipeline stays clean.

🤖 Generated with [Claude Code](https://claude.com/claude-code)















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28690999781](https://github.com/sgl-project/sglang/actions/runs/28690999781)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28690999707](https://github.com/sgl-project/sglang/actions/runs/28690999707)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
