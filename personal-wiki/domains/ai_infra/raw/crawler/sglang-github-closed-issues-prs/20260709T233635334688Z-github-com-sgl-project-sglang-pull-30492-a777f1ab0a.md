---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Adopt get_parallel() everywhere and close out the parallel wrapper
  surface'
canonical_url: https://github.com/sgl-project/sglang/pull/30492
captured_at: '2026-07-09T23:36:35.334688+00:00'
content_hash: a777f1ab0ad1fb118ad1a0e5fe477f036088990babdb1327922fcc4445d5a1ec
---
# [refactor] Adopt get_parallel() everywhere and close out the parallel wrapper surface

URL: https://github.com/sgl-project/sglang/pull/30492
State: closed
Labels: deepseek, speculative-decoding, npu
Closed at: 2026-07-09T09:09:40Z
Merged at: 2026-07-09T09:09:40Z

## Motivation

`runtime_context.ParallelContext` is the read-through surface for parallel topology, but adoption had gaps: the decode-context-parallel dimension was never wrapped, a few files regressed back to raw getters inside the already-swept directories, `dp_attention` still exported a re-export family shadowing the canonical accessors, and ~150 call sites outside the original sweep still read the raw getters directly.

## Modifications

- Wrap decode context parallel on the wrapper (`dcp_size` / `dcp_rank` / `dcp_group`).
- Flip the remaining direct reads of the parallel-state getters package-wide to `get_parallel()`; delete the `dp_attention` re-export family (`get_attention_tp_group` etc.); retire the never-read `_LOCAL_ATTN_DP_SIZE` / `_LOCAL_ATTN_DP_RANK` pair and `compute_dp_attention_local_info`.
- Land an adoption ratchet pinning raw-getter call-site counts (exempting the owning modules: `distributed/`, `dp_attention.py`, and the debug dumper whose megatron plugin uses same-named third-party getters).
- Tests that monkeypatched module import bindings for the getters switch to `get_parallel().override(...)` (the patched bindings no longer exist after the sweep).

## Verification

Full unit suite name-identical to base; attention unittest tree green (179 passed, 538 subtests); DeepSeek-V3.2 tp2 smoke through the flipped hot paths.

Stacked on #30491.

🤖 Generated with [Claude Code](https://claude.com/claude-code)



























































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29007210475](https://github.com/sgl-project/sglang/actions/runs/29007210475)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29007210262](https://github.com/sgl-project/sglang/actions/runs/29007210262)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
