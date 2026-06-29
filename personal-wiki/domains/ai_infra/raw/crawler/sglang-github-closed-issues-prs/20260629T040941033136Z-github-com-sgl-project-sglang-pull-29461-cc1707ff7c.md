---
source_id: sglang-github-closed-issues-prs
title: Fix FlashInfer A2A dispatcher during CUDA graph capture
canonical_url: https://github.com/sgl-project/sglang/pull/29461
captured_at: '2026-06-29T04:09:41.033136+00:00'
content_hash: cc1707ff7cea7c3e680827a0913737d8dff722036c6dca796b2c657d75be4ad6
---
# Fix FlashInfer A2A dispatcher during CUDA graph capture

URL: https://github.com/sgl-project/sglang/pull/29461
State: closed
Labels: run-ci
Closed at: 2026-06-28T09:21:27Z
Merged at: 2026-06-28T09:21:27Z

## Summary
- Skip the EP>1 runtime token count query branch during CUDA graph capture in the FlashInfer MoE A2A dispatcher.
- The captured graph uses fixed geometry, so querying runtime token counts via NCCL all-gather during capture is incorrect.
- Gate the branch on `not is_graph_capture` (combining `get_is_capture_mode()` and `is_in_breakable_cuda_graph()`).

## Original commits
- `d3abe7396`

























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28311737180](https://github.com/sgl-project/sglang/actions/runs/28311737180)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28311737102](https://github.com/sgl-project/sglang/actions/runs/28311737102)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
