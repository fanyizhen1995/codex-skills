---
source_id: sglang-github-closed-issues-prs
title: '[sglang-miles] Cherry-pick #26980: Skip routed expert capture for draft model
  under spec v2'
canonical_url: https://github.com/sgl-project/sglang/pull/29685
captured_at: '2026-07-01T02:12:08.972412+00:00'
content_hash: 0adeb0a75845473a8ddd5eb9a0a2828c4656b270ceef415edce73a35e905f6be
---
# [sglang-miles] Cherry-pick #26980: Skip routed expert capture for draft model under spec v2

URL: https://github.com/sgl-project/sglang/pull/29685
State: closed
Labels: 
Closed at: 2026-06-29T23:00:59Z
Merged at: 2026-06-29T23:00:59Z

## Summary

Cherry-pick of upstream #26980 onto `sglang-miles`: stop a speculative MoE draft from polluting the target's routed-experts capture.

Original PR: https://github.com/sgl-project/sglang/pull/26980 (merged as `e4bf0043`).

## What lands here

- `TopKConfig.allow_routed_experts_capture` (default `True`) gates the single capture site `capture_routed_experts_if_allowed`, on both the CUDA `_post_process_topk_ids` and NPU `fused_topk_npu` paths.
- `ModelRunner.initialize` calls `disable_routed_experts_capture_for_draft(self.model)` on every draft worker, before any backend/graph init.
- `init_routed_experts_capturer` early-returns for a draft worker, so it never reinstalls the process-global capturer.

## Cherry-pick notes

- One conflict in `model_runner.py`, resolved by keeping the `sglang-miles` `cuda_graph_num_tokens` block (used below as `cuda_graph_batch=`) and applying #26980's three remaining hunks (import, draft opt-out in `initialize`, draft early-return in `init_routed_experts_capturer`).
- The `not self.is_draft_worker` gate on `on_forward_end` (hunk 4 of #26980) was **already present** in `sglang-miles`, so it produces no diff here.
- The other four files (`hardware_backend/npu/moe/topk.py`, `fused_moe_triton/layer.py`, `layers/moe/topk.py`, `state_capturer/routed_experts.py`) apply with diffs identical to the original commit.
- Upstream #26980's added tests are not included (the merged commit itself dropped them).











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28407981981](https://github.com/sgl-project/sglang/actions/runs/28407981981)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28407981803](https://github.com/sgl-project/sglang/actions/runs/28407981803)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
