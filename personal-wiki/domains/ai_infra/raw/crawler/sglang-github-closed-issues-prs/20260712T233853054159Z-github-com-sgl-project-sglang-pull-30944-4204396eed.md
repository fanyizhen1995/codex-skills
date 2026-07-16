---
source_id: sglang-github-closed-issues-prs
title: '[Spec] Add kill-switch env for draft-extend CUDA graph capture'
canonical_url: https://github.com/sgl-project/sglang/pull/30944
captured_at: '2026-07-12T23:38:53.054159+00:00'
content_hash: 4204396eed4959231b1fc6f7caa3b2ca660c54e3c16d27bd668217633585c0ef
---
# [Spec] Add kill-switch env for draft-extend CUDA graph capture

URL: https://github.com/sgl-project/sglang/pull/30944
State: closed
Labels: deepseek
Closed at: 2026-07-12T19:54:36Z
Merged at: 2026-07-12T19:54:36Z

Adds `SGLANG_DISABLE_DRAFT_EXTEND_CUDA_GRAPH` to force draft extend to run eager, and sets it in `test_deepseek_v4_flash_fp4_b200_cp.py` where the draft-extend graph pool costs ~4.5 GB and OOMs the eager prefill draft extend (see https://github.com/sgl-project/sglang/pull/30853#issuecomment-4951235511).

## Follow-up

The draft-extend graph enablement logic is fragmented and should be unified:

- The capture decision is duplicated across two workers (`eagle_worker_v2.py` and `multi_layer_eagle_worker_v2.py`), each hardcoding its own platform / supported-backend checks; this PR's kill-switch had to be wired into both sites separately.
- Draft-extend graphs live entirely outside the `cuda_graph_config` phase framework: there is no per-phase `backend` / `bs` / `max_bs` control for them, and the capture bs list is borrowed from the decode phase.

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29206097067](https://github.com/sgl-project/sglang/actions/runs/29206097067)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29206096970](https://github.com/sgl-project/sglang/actions/runs/29206096970)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
