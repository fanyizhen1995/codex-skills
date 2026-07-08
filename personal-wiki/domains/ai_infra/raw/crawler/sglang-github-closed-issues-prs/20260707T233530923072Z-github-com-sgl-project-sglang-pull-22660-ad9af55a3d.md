---
source_id: sglang-github-closed-issues-prs
title: Skip redundant moe_sum_reduce for single-expert routing on XPU
canonical_url: https://github.com/sgl-project/sglang/pull/22660
captured_at: '2026-07-07T23:35:30.923072+00:00'
content_hash: ad9af55a3d27a7e715ab50edeb73b28174a9108a8acf11ee54bfd6f5435f6390
---
# Skip redundant moe_sum_reduce for single-expert routing on XPU

URL: https://github.com/sgl-project/sglang/pull/22660
State: closed
Labels: intel, xpu, run-ci, run-ci-extra
Closed at: 2026-07-07T01:03:16Z
Merged at: 2026-07-07T01:03:16Z

When topk_ids.shape[1] == 1 and routed_scaling_factor == 1.0, the second invoke_fused_moe_kernel call already writes its output directly into out_hidden_states, so the subsequent moe_sum_reduce is a no-op reduction over a single element. This adds an early-exit check on the XPU path to skip the unnecessary kernel launch, matching the existing optimization already present in the CUDA path.

This is particularly relevant for Llama-4-Scout models (e.g. Llama-4-Scout-17B-16E-Instruct), which set num_experts_per_tok = 1, meaning this fast path is hit on every MoE layer forward pass.

































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28767828252](https://github.com/sgl-project/sglang/actions/runs/28767828252)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28767828170](https://github.com/sgl-project/sglang/actions/runs/28767828170)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
