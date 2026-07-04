---
source_id: sglang-github-closed-issues-prs
title: Fix capture-mode detection during breakable CUDA graph capture
canonical_url: https://github.com/sgl-project/sglang/pull/29866
captured_at: '2026-07-03T02:13:21.704139+00:00'
content_hash: 2d1b812fb3f52f8148e86ea827bcc214d812b23c70adc09e68dc01bdf6fc0a54
---
# Fix capture-mode detection during breakable CUDA graph capture

URL: https://github.com/sgl-project/sglang/pull/29866
State: closed
Labels: run-ci, run-ci-extra
Closed at: 2026-07-02T05:12:57Z
Merged at: 2026-07-02T05:12:57Z

### Problem
Prefill's breakable CUDA graph (BCG) captured a `max_num_tokens` (e.g. 4096) EP all-to-all buffer (~2GB) instead of the actual `x.shape[0]` (~512).

### Cause
Prefill BCG capture doesn't enter `model_capture_mode()`, so `get_is_capture_mode()` was `False` during BCG capture. The FlashInfer a2a dispatcher's Case-2 guard (`not get_is_capture_mode()`) then treated capture as live inference and sized the buffer to the static max.

### Fix
`get_is_capture_mode()` also returns `True` when `is_in_breakable_cuda_graph()`, restoring correct capture detection at the source. Empirically validated on gb300x4 (tp4ep4, ep=4, no DP attn): prefill BCG `runtime_max_tokens_per_rank` 4096 -> 512.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28539749835](https://github.com/sgl-project/sglang/actions/runs/28539749835)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28539748815](https://github.com/sgl-project/sglang/actions/runs/28539748815)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
