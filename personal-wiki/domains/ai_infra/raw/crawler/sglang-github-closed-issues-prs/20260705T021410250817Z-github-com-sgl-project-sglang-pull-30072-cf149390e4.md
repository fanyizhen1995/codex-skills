---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Add the post-process resolution stage; migrate sampling_backend
  (stack 10/15)'
canonical_url: https://github.com/sgl-project/sglang/pull/30072
captured_at: '2026-07-05T02:14:10.250817+00:00'
content_hash: cf149390e4d2e96527015aa2ab36a0d308326d3f5ebc19c5963e318323da92a6
---
# [refactor] Add the post-process resolution stage; migrate sampling_backend (stack 10/15)

URL: https://github.com/sgl-project/sglang/pull/30072
State: closed
Labels: 
Closed at: 2026-07-04T09:22:06Z
Merged at: 2026-07-04T09:22:06Z

Normalization handlers become ordered declarative passes:
- ResolvedView is the read-only pass input (during the dual-apply
  transition it forwards to the live server_args at the legacy slot —
  exactly what the imperative handler observed; end-state it overlays
  accumulated declarations on the pristine object). Writes raise.
- register_post_process / POST_PROCESS_PASSES (list order = end-state
  execution order) + run_post_process_pass (legacy-slot invocation:
  evaluate on the live view, append to the stash, dual-apply in place).
- First field-complete template: _sampling_backend_default (flashinfer
  availability fill) + _deterministic_sampling_backend (force pytorch
  unless ascend), a two-writer provenance chain with last-writer-wins;
  the earlier platform-handler writes stay imperative and are observed
  through the live view.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

---
Part 10/15 of the declarative config-resolution stack (based on `cheng/gc-pr-09`). Full-stack CI runs on the top PR #30062; `run-ci` is added per PR as it reaches the front of the merge order.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28701795526](https://github.com/sgl-project/sglang/actions/runs/28701795526)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28701795331](https://github.com/sgl-project/sglang/actions/runs/28701795331)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
