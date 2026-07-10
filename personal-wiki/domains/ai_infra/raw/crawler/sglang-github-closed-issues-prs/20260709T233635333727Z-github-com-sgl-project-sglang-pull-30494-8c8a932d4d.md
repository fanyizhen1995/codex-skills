---
source_id: sglang-github-closed-issues-prs
title: '[docs] Add the sglang-runtime-context skill'
canonical_url: https://github.com/sgl-project/sglang/pull/30494
captured_at: '2026-07-09T23:36:35.333727+00:00'
content_hash: 8c8a932d4d7410aaf70efe33ddbbbcfa7dd739710c8adfd9598e87eb794c1f04
---
# [docs] Add the sglang-runtime-context skill

URL: https://github.com/sgl-project/sglang/pull/30494
State: closed
Labels: documentation
Closed at: 2026-07-09T09:11:37Z
Merged at: 2026-07-09T09:11:36Z

## Motivation

The runtime-context architecture now spans several tiers and CI guardrails; contributors (and coding agents) need one onboarding reference for how to read and mutate configuration, declare model-specific adjustments, and test against it.

## Modifications

Adds the `sglang-runtime-context` skill under `.claude/skills/`: the five tiers on `RuntimeContext` (resolved-at-end config, runtime flag groups, resources with named stream/buffer leases, per-forward flags, the parallel wrapper), the developer contract (`ServerArgs.override` as the single post-resolution mutation entry, model-override declaration via the registry and passes, the load-time vs resolution-time rule), testing idioms (override causes not effects; never patch import bindings), what each CI guardrail enforces and what to do when it fires, and a pitfall checklist.

Docs only; describes mechanisms already on main plus the in-flight refactor series.

🤖 Generated with [Claude Code](https://claude.com/claude-code)



































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29007303890](https://github.com/sgl-project/sglang/actions/runs/29007303890)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29007303669](https://github.com/sgl-project/sglang/actions/runs/29007303669)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
