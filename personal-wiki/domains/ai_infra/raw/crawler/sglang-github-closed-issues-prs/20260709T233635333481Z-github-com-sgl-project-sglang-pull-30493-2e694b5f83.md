---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Retire the legacy config accessor and the remaining process singletons'
canonical_url: https://github.com/sgl-project/sglang/pull/30493
captured_at: '2026-07-09T23:36:35.333481+00:00'
content_hash: 2e694b5f83b4a354ee5854b0c05f482ba66eeb16720207302259b9ccc4059667
---
# [refactor] Retire the legacy config accessor and the remaining process singletons

URL: https://github.com/sgl-project/sglang/pull/30493
State: closed
Labels: amd, Multi-modal, deepseek, speculative-decoding, blackwell, npu, mthreads, apple-silicon
Closed at: 2026-07-09T09:10:48Z
Merged at: 2026-07-09T09:10:48Z

## Motivation

The config tier has one blessed accessor (`runtime_context.get_server_args`) but 280 call sites still went through the legacy `get_global_server_args` name; a few process singletons (the indexer/routed-experts state capturers, the shared TCPStore, the trace verbosity level) still lived as module globals outside the context lifecycle; and the attention unit-test kit hand-built and published mock `ServerArgs` objects instead of driving execution through the context.

## Modifications

- Flip all 280 `get_global_server_args()` call-sites (126 files) to `get_server_args()`. Imports are flipped in the scope they had (function-scope late imports stay put, so no new import cycles); the `model_runner` re-export surface is kept; the legacy-accessor ratchet is pinned to the shim definition itself, which stays for out-of-tree callers.
- Move the remaining singletons onto `ctx.resources` slots. Accessors stay byte-identical shims; the trace level keeps its `SGLANG_TRACE_LEVEL`-seeded default by seeding lazily in the getter, so `reset_context()` returns it to the environment default.
- Add `get_context().override_server_args(**fields)`: the config tier's scoped test override (sibling of `get_parallel().override()` and the flag groups' `override()`). It publishes a fresh dummy-boundary `ServerArgs` carrying the overrides — written through `ServerArgs.override` for provenance — and restores the previous publish state on exit. The attention-kit fixtures adopt it and their hand-built factory is deleted together with its mutation-ratchet exemption. The primitive is documented as transitional: as runtime code migrates off raw config-field branching onto the named runtime tiers, the finer-grained overrides take over and this one retires.

## Verification

Full unit suite name-identical to base; attention unittest tree 179 passed / 0 failed (538 subtests); all four guardrail ratchets green.

Stacked on #30492.

🤖 Generated with [Claude Code](https://claude.com/claude-code)















































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29007271619](https://github.com/sgl-project/sglang/actions/runs/29007271619)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29007271334](https://github.com/sgl-project/sglang/actions/runs/29007271334)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
