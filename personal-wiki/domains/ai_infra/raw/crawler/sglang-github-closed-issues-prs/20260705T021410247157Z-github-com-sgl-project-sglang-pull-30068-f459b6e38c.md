---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Wire the config resolution pipeline (dispatch, stash, dual-apply,
  publish) (stack 6/15)'
canonical_url: https://github.com/sgl-project/sglang/pull/30068
captured_at: '2026-07-05T02:14:10.247157+00:00'
content_hash: f459b6e38caf9de19c1f0a3193960d33607a06459a1e5ac8707d26843a1430f1
---
# [refactor] Wire the config resolution pipeline (dispatch, stash, dual-apply, publish) (stack 6/15)

URL: https://github.com/sgl-project/sglang/pull/30068
State: closed
Labels: 
Closed at: 2026-07-04T09:21:21Z
Merged at: 2026-07-04T09:21:21Z

A strict no-op while the registry is empty:
- _handle_model_specific_adjustments dispatches the registry at the
  head of the arch-branch section: declarations are collected on the
  pristine config, stashed on the instance (computed once; the stash
  travels with the object across processes), and dual-applied in place.
- Publishing resolves the stash into the flags tier through the gate
  and asserts flag/server_args parity for declared fields; publishes
  without a stash (dummy/none fixtures, test-kit mocks) skip
  resolution; resolution runs before the slot write so a failed
  resolution leaves the previous publish intact.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

---
Part 6/15 of the declarative config-resolution stack (based on `cheng/gc-pr-05`). Full-stack CI runs on the top PR #30062; `run-ci` is added per PR as it reaches the front of the merge order.

🤖 Generated with [Claude Code](https://claude.com/claude-code)







































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28701778832](https://github.com/sgl-project/sglang/actions/runs/28701778832)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28701778629](https://github.com/sgl-project/sglang/actions/runs/28701778629)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
