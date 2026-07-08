---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Add the declarative model-override registry and resolution gate
  (stack 5/15)'
canonical_url: https://github.com/sgl-project/sglang/pull/30067
captured_at: '2026-07-05T02:14:10.252608+00:00'
content_hash: cb6900d57318012daa028c493ae42440b5096c067e290f658a315a341a3e6c94
---
# [refactor] Add the declarative model-override registry and resolution gate (stack 5/15)

URL: https://github.com/sgl-project/sglang/pull/30067
State: closed
Labels: 
Closed at: 2026-07-04T09:21:10Z
Merged at: 2026-07-04T09:21:10Z

Purely additive; no production caller (the whitelist is empty, so the
gate is a no-op in the tree):
- MODEL_OVERRIDES const table + @register_model_override(arch):
  providers receive the pristine (server_args, model_config) read-only
  and RETURN declaration dicts; collection order is const first, then
  callables in registration order.
- apply_model_overrides: the single transactional resolution point —
  validates every declaration against the whitelist and the flag-leaf
  layout before any write; declarations apply in order (last writer
  wins) with a terminal pass applying after everything; every
  whitelisted field materializes as a flag leaf (undeclared = pristine
  value) so readers never fall back to config; returns a provenance log
  chaining writers.
- apply_declarations_to_server_args (transition dual-apply, replaying
  declarations byte-identically to the legacy imperative writes) +
  assert_flag_parity (drift guard).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

---
Part 5/15 of the declarative config-resolution stack (based on `cheng/gc-pr-04`). Full-stack CI runs on the top PR #30062; `run-ci` is added per PR as it reaches the front of the merge order.

🤖 Generated with [Claude Code](https://claude.com/claude-code)





































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28701774655](https://github.com/sgl-project/sglang/actions/runs/28701774655)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28701774546](https://github.com/sgl-project/sglang/actions/runs/28701774546)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
