---
source_id: sglang-github-closed-issues-prs
title: '[fix] Reconcile the legacy-getter ratchet baseline after racing merges'
canonical_url: https://github.com/sgl-project/sglang/pull/30154
captured_at: '2026-07-06T02:14:53.060778+00:00'
content_hash: 8c246e75bccb4659e00de46b70cc54f0cb9b6e355233e86ae815471964b87e56
---
# [fix] Reconcile the legacy-getter ratchet baseline after racing merges

URL: https://github.com/sgl-project/sglang/pull/30154
State: closed
Labels: run-ci
Closed at: 2026-07-05T14:06:07Z
Merged at: 2026-07-05T14:06:07Z

The config-resolution series (#30137) pinned the `get_global_server_args` exact-pin baseline at 278, and #28787 concurrently added two call sites in `layernorm.py` (`rl_on_policy_target` reads on the ROCm batch-invariant path). Both were green against their own merge bases, but the combined tree counts 280, so `test_legacy_global_ratchet` now fails on main and on every PR's merge commit running the cpu base suite. This bumps the baseline to the actual count.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28736829308](https://github.com/sgl-project/sglang/actions/runs/28736829308)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28736832931](https://github.com/sgl-project/sglang/actions/runs/28736832931)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
