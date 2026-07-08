---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Move ServerArgs ownership into the runtime context (stack 2/15)'
canonical_url: https://github.com/sgl-project/sglang/pull/30064
captured_at: '2026-07-05T02:14:10.254446+00:00'
content_hash: 32c5d9ff6bb5bbcc87c35b3115c29a06da7467268c62ce4fe6b0543c425613c4
---
# [refactor] Move ServerArgs ownership into the runtime context (stack 2/15)

URL: https://github.com/sgl-project/sglang/pull/30064
State: closed
Labels: ready-to-merge, diffusion
Closed at: 2026-07-04T09:20:34Z
Merged at: 2026-07-04T09:20:34Z

Behavior byte-equivalent ownership flip:
- RuntimeContext owns the storage slot; set_server_args() publishes
  (overwrite-allowed, matching today's semantics) and reset_context()
  clears it for unit-test teardown.
- get_global_server_args / set_global_server_args_for_scheduler (and
  the tokenizer alias) become identity-preserving shims over the slot:
  same names, signatures, semantics; the object is returned by
  reference so every post-publish mutation site keeps writing the one
  live instance. The _global_server_args module global is deleted;
  delegation reverses to lazy in-function imports (cycle-free, verified
  by cold import).
- One test helper reached into the private module global and is
  migrated to public API; all other publish/read call-sites unchanged.
- Tests: shim identity both directions, verbatim pre-publish error,
  overwrite-allow, reset, and a guard that the legacy global stays
  deleted.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

---
Part 2/15 of the declarative config-resolution stack (based on `cheng/gc-pr-01`). Full-stack CI runs on the top PR #30062; `run-ci` is added per PR as it reaches the front of the merge order.

🤖 Generated with [Claude Code](https://claude.com/claude-code)



















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28701759857](https://github.com/sgl-project/sglang/actions/runs/28701759857)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28701759773](https://github.com/sgl-project/sglang/actions/runs/28701759773)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
