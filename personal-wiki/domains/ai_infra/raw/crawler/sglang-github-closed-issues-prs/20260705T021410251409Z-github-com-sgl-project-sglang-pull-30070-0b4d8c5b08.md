---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Add predicate-keyed registration; migrate the Step3p family (stack
  8/15)'
canonical_url: https://github.com/sgl-project/sglang/pull/30070
captured_at: '2026-07-05T02:14:10.251409+00:00'
content_hash: 0b4d8c5b08bd3cd04fb0567a29e2172bdb6d14560dd1e558d543396a1fa2d35b
---
# [refactor] Add predicate-keyed registration; migrate the Step3p family (stack 8/15)

URL: https://github.com/sgl-project/sglang/pull/30070
State: closed
Labels: 
Closed at: 2026-07-04T09:21:44Z
Merged at: 2026-07-04T09:21:44Z

register_model_override_predicate covers legacy branches matched by
substring on the architecture; collection order (const -> exact ->
predicate) is pinned by test. The Step3p EAGLE and hierarchical-cache
SWA writes become declarations (whitelist + flat leaves for
swa_full_tokens_ratio / disable_hybrid_swa_memory); the
platform-conditional attention selection stays in the branch for a
later batch.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

---
Part 8/15 of the declarative config-resolution stack (based on `cheng/gc-pr-07`). Full-stack CI runs on the top PR #30062; `run-ci` is added per PR as it reaches the front of the merge order.

🤖 Generated with [Claude Code](https://claude.com/claude-code)





































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28701786337](https://github.com/sgl-project/sglang/actions/runs/28701786337)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28701786285](https://github.com/sgl-project/sglang/actions/runs/28701786285)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
