---
source_id: sglang-github-closed-issues-prs
title: Fix EAGLE draft hidden dim extraction and centralize spec helpers
canonical_url: https://github.com/sgl-project/sglang/pull/29464
captured_at: '2026-06-29T04:09:41.035538+00:00'
content_hash: f6a16902f97f9efbb1a5344bb677da2a86b5ce105e13cc26c0c4f67aa3563f12
---
# Fix EAGLE draft hidden dim extraction and centralize spec helpers

URL: https://github.com/sgl-project/sglang/pull/29464
State: closed
Labels: run-ci
Closed at: 2026-06-28T04:48:26Z
Merged at: 2026-06-28T04:48:26Z

## Summary
- Consolidate hidden-state width/dtype resolution for EAGLE speculative decoding into two centralized helpers in `eagle_utils.py`:
  - `get_draft_input_from_target_hidden_dim`: derives the target hidden states width from config (handles EAGLE3 aux mode). Replaces reading from `fc.in_features` which is incorrect for some architectures.
  - `get_draft_recurrent_hidden_state_spec`: returns hidden_states width/dtype for draft decode steps. Replaces scattered `hidden_size_for`/`dtype_for` classmethods.
- Fix prefill CUDA graph runner to copy `input_embeds` into the static BCG slot before replay for multimodal batches.
- Use `supports_target_verify_for_draft()` instead of `is_dflash()` for the draft-worker guard.
- PEP 617 parenthesized context managers.

## Original commits
- `004cc6a43`































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28271700183](https://github.com/sgl-project/sglang/actions/runs/28271700183)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28271700103](https://github.com/sgl-project/sglang/actions/runs/28271700103)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
