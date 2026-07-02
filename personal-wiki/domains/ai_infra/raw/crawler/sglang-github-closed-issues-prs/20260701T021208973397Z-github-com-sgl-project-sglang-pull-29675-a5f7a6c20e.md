---
source_id: sglang-github-closed-issues-prs
title: '[sglang-miles] Cherry-pick pause-aware post-process weight locking'
canonical_url: https://github.com/sgl-project/sglang/pull/29675
captured_at: '2026-07-01T02:12:08.973397+00:00'
content_hash: a5f7a6c20e2669362931059731b92a085534d7087ee8e0c955d2037eae70a406
---
# [sglang-miles] Cherry-pick pause-aware post-process weight locking

URL: https://github.com/sgl-project/sglang/pull/29675
State: closed
Labels: 
Closed at: 2026-06-29T22:22:32Z
Merged at: 2026-06-29T22:22:32Z

Cherry-picks sgl-project/sglang#29670 onto `sglang-miles`.\n\nOriginal commit: 23d989874bd1d467fac54c7f6d138166736f438b\nCherry-pick commit: 2629867c5bc460bd1802d8c59d36403675ffa1b0\n\nConflict resolution:\n- Adapted the original `post_process_weights` pause-aware locking fix to the refactored `begin_weight_update` / `end_weight_update` APIs currently present on `sglang-miles`.\n- Preserved the original behavior: paused updates run without `model_update_lock.writer_lock` while holding `is_pause_cond`; unpaused updates use the writer lock.\n\nValidation:\n- Cherry-pick commit hooks passed: Python AST, merge-conflict check, isort, ruff, and related pre-commit checks.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28401848370](https://github.com/sgl-project/sglang/actions/runs/28401848370)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28401847995](https://github.com/sgl-project/sglang/actions/runs/28401847995)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
