---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Collect MoE and DP-attention runtime state into typed flag groups'
canonical_url: https://github.com/sgl-project/sglang/pull/30347
captured_at: '2026-07-08T23:36:33.798382+00:00'
content_hash: 4f4d69e7360bd838df49cb569b6ac925a440534a294750e6f75121b25e345fa3
---
# [refactor] Collect MoE and DP-attention runtime state into typed flag groups

URL: https://github.com/sgl-project/sglang/pull/30347
State: closed
Labels: amd, ready-to-merge
Closed at: 2026-07-08T04:29:28Z
Merged at: 2026-07-08T04:29:28Z

## Motivation

`layers/moe/utils.py` kept twelve module-level globals (parsed backend enums, deepep mode/config, overlap switches, and two ACTIVE values swapped by the speculative contexts), and `dp_attention.py` kept the DP-attention enable/max-len flags — per-module runtime state with ad-hoc lifecycle that leaks across unit-test teardowns and can only be forced in tests by rebinding import names.

## Modifications

- **`flags.moe`**: `initialize_moe_config` materializes the group at its existing call site; every accessor keeps its exact signature and lazy-default behavior, so the 137 `get_moe_a2a_backend` / 93 `get_moe_runner_backend` call sites are untouched. The speculative backend contexts swap the group leaves with the same enter/exit/exception semantics (the a2a context still co-swaps `disable_fp4_allgather`).
- **`flags.dp`**: `is_dp_attention_enabled` (73 sites) becomes a thin shim over the leaf; the hybrid-SSM max-len marker moves with it. Topology values stay on the module for the parallel vertical.
- **Module-state ratchet**: an AST-based pin of the `global` statements allowed in the two files (topology quartet only); a new module-level runtime global fails the test.
- **Test injection converges** on `get_flags().<group>.override(...)` — the two tests that patched import bindings (one of which never restored the binding) now force the flag itself.

## Verification

Full unit suite name-identical to base; group unit tests (materialize / swap / nesting / exception restore / lazy defaults); DSV3.2 tp2 and Nemotron-3-Nano tp4/dp2 dp-attention smokes.

Stacked on the read-convergence PR.

🤖 Generated with [Claude Code](https://claude.com/claude-code)









































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28917572539](https://github.com/sgl-project/sglang/actions/runs/28917572539)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28917572427](https://github.com/sgl-project/sglang/actions/runs/28917572427)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
