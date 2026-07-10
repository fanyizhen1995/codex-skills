---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Global Context: post-resolve-at-end stack review (override entry,
  field convergence, flag groups, resources)'
canonical_url: https://github.com/sgl-project/sglang/pull/30349
captured_at: '2026-07-09T23:36:35.333960+00:00'
content_hash: 9a7313e96d4b8f6e12b3eed722f50eda87fbca014ddf97b42bd3ef8230e35210
---
# [refactor] Global Context: post-resolve-at-end stack review (override entry, field convergence, flag groups, resources)

URL: https://github.com/sgl-project/sglang/pull/30349
State: closed
Labels: documentation, amd, lora, Multi-modal, deepseek, speculative-decoding, blackwell, npu, run-ci, piecewise-cuda-graph, mthreads, apple-silicon, bypass-fastfail, run-ci-extra
Closed at: 2026-07-09T09:11:55Z
Merged at: 

## Motivation

Full-stack review & CI carrier for the remaining Global Context series (post-#30297/#30299/#30346–#30348, which are already merged). This PR aggregates the whole remaining stack against `main` so CI runs the combined diff; the member PRs carry the per-unit review:

- #30489 — EP dispatcher + fusion-workspace manager state onto `ctx.resources`
- #30490 — per-forward flags tier: `ctx.forward` (contextvar-backed, `scoped()` write path)
- #30491 — DP gathered-buffer state split between `flags.dp` and `ctx.forward`
- #30492 — adopt `get_parallel()` everywhere; DCP dims; retire the `dp_attention` re-export family; adoption ratchet
- #30493 — retire `get_global_server_args` call-sites (280 → shim only); remaining singletons onto `ctx.resources`; `override_server_args` scoped test override (transitional)

(#30494 — the runtime-context skill doc — is docs-only and based on `main` directly.)

Contains a `STACK_REVIEW_PLACEHOLDER.md` marker (removed before/at merge; this PR is not merged as-is — members merge one by one).

## Verification

Full unit suite (strict mutation guard on) name-by-name identical to the post-merge `main` baseline; four guardrail ratchets green (mutation exact-pin 0, legacy accessor pin 1, module-state, parallel adoption); attention unittest tree 179 passed / 0 failed (538 subtests); DSV3.2 tp2, Nemotron tp4/dp2 dp-attention, and GLM-4.7-Flash (default + flashinfer) smokes.

🤖 Generated with [Claude Code](https://claude.com/claude-code)









































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28984424087](https://github.com/sgl-project/sglang/actions/runs/28984424087)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28984423984](https://github.com/sgl-project/sglang/actions/runs/28984423984)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
