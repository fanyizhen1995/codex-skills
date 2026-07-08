---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Sweep disable_hybrid_swa_memory writers; close the dtype family
  (stack 9/15)'
canonical_url: https://github.com/sgl-project/sglang/pull/30071
captured_at: '2026-07-05T02:14:10.246552+00:00'
content_hash: 0dccb7d24865dab674a78991abfd52f74864d67decbdc47f34a701009989af17
---
# [refactor] Sweep disable_hybrid_swa_memory writers; close the dtype family (stack 9/15)

URL: https://github.com/sgl-project/sglang/pull/30071
State: closed
Labels: 
Closed at: 2026-07-04T09:21:55Z
Merged at: 2026-07-04T09:21:55Z

Field-family sweep at zero new whitelist cost: Gemma2/Gemma3 (the whole
branch dissolves), Exaone (conditional write; the explicit-backend
assert stays), Olmo2 (write moves; attention selection stays). GptOss
mxfp4 -> dtype joins as the first model-config-derived declaration,
with the XPU dtype validation moving into the same callable (it reads
the pristine request, exactly what the legacy mid-branch read saw) —
every dtype writer inside the arch monolith is now declarative.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

---
Part 9/15 of the declarative config-resolution stack (based on `cheng/gc-pr-08`). Full-stack CI runs on the top PR #30062; `run-ci` is added per PR as it reaches the front of the merge order.

🤖 Generated with [Claude Code](https://claude.com/claude-code)











































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28701790814](https://github.com/sgl-project/sglang/actions/runs/28701790814)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28701790701](https://github.com/sgl-project/sglang/actions/runs/28701790701)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
