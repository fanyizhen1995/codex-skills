---
source_id: sglang-github-closed-issues-prs
title: '[Cherry-pick to release/v0.5.15] [DeepSeek V2] Reorder dual-stream MoE to
  main-first to avoid CUDA graph stream explosion (#30460)'
canonical_url: https://github.com/sgl-project/sglang/pull/30714
captured_at: '2026-07-10T23:37:20.335726+00:00'
content_hash: a09a87592d09e2b2137ae5b0b40e4fd4e40621303af7401196ef805245d47976
---
# [Cherry-pick to release/v0.5.15] [DeepSeek V2] Reorder dual-stream MoE to main-first to avoid CUDA graph stream explosion (#30460)

URL: https://github.com/sgl-project/sglang/pull/30714
State: closed
Labels: deepseek, cherry-pick
Closed at: 2026-07-10T00:35:11Z
Merged at: 2026-07-10T00:35:11Z

Cherry-pick of #30460 (commit 87992eeec4072995e8fa98fb2d0f3a7e5e581f2d) onto `release/v0.5.15`.

The automated bot cherry-pick was not used because the pick conflicts on this branch: `release/v0.5.15` still uses `get_global_server_args()` while main renamed it to `get_server_args()`. The conflict was resolved by keeping the branch's `get_global_server_args()` API; everything else applies unchanged (verified the `disable_dispose_tensor` flag, `model_capture_mode` hook, and `dispose_tensor` guard all landed intact, and `has_shared_output` matches this branch's `_forward_shared_experts` non-None condition).

🤖 Generated with [Claude Code](https://claude.com/claude-code)















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29059957105](https://github.com/sgl-project/sglang/actions/runs/29059957105)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #29059957060](https://github.com/sgl-project/sglang/actions/runs/29059957060)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
