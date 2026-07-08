---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Add the resolved-flags tier + resolvable-field metadata (stack
  4/15)'
canonical_url: https://github.com/sgl-project/sglang/pull/30066
captured_at: '2026-07-05T02:14:10.253817+00:00'
content_hash: 00ac00792e33132f9ce241ade5b8a9b7ed9ebda7f32a7c6d44246f8a6b0a78a0
---
# [refactor] Add the resolved-flags tier + resolvable-field metadata (stack 4/15)

URL: https://github.com/sgl-project/sglang/pull/30066
State: closed
Labels: 
Closed at: 2026-07-04T09:20:58Z
Merged at: 2026-07-04T09:20:58Z

Purely additive skeleton for declarative config resolution:
- Flag groups are typed dataclasses (__dataclass_fields__ is the single
  source of truth; typos raise); _StaticFlags groups are writable during
  resolution and locked by freeze(); each group has a transactional
  test-only override(**kw) usable on frozen groups. Flags container
  holds attn/moe family groups and a never-frozen capture group;
  FLAG_LEAF_MAP routes resolved fields to leaves (flat by default).
  ctx.flags + get_flags(); reset_context() installs a fresh Flags.
- Arg gains model_overridable (default False) and
  model_overridable_fields() derives the whitelist from Annotated
  metadata; a pin test asserts the ServerArgs whitelist stays exactly
  the migrated set so accidental tagging fails loudly.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

---
Part 4/15 of the declarative config-resolution stack (based on `cheng/gc-pr-03`). Full-stack CI runs on the top PR #30062; `run-ci` is added per PR as it reaches the front of the merge order.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

























































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28701771215](https://github.com/sgl-project/sglang/actions/runs/28701771215)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28701771159](https://github.com/sgl-project/sglang/actions/runs/28701771159)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
