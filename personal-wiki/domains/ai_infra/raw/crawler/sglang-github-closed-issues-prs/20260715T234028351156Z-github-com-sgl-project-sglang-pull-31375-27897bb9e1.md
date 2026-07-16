---
source_id: sglang-github-closed-issues-prs
title: '[Spec] Extract the shared draft() tail into build_eagle_verify_input'
canonical_url: https://github.com/sgl-project/sglang/pull/31375
captured_at: '2026-07-15T23:40:28.351156+00:00'
content_hash: 27897bb9e16cd323a0b833c9d93511627c6e8f0de8fe60ff420e65df056def7f
---
# [Spec] Extract the shared draft() tail into build_eagle_verify_input

URL: https://github.com/sgl-project/sglang/pull/31375
State: closed
Labels: 
Closed at: 2026-07-15T22:59:32Z
Merged at: 2026-07-15T22:59:32Z

Consolidate the identical tail of `EagleDraftWorker.draft()` and `MultiLayerEagleDraftWorker.draft()` (idle-input creation, tree-mask build via `build_tree_kernel_efficient`, `EagleVerifyInput` assembly) into one `eagle_worker_common.build_eagle_verify_input` function; each `draft()` keeps its own forward logic and now ends with a single call.

## Verification (machine-checked)

Verification script: https://gist.github.com/hnyls2002/4e4512697bbceca34b3788ad3e7b9c72 — runs against the pinned base/head commits and re-derives both proofs:

1. **Consolidation proof**: at the base commit, the two `draft()` tails are byte-identical after the declared transforms (dedent by 4; six `self.<attr>` -> parameter renames; multi-layer's `draft_probs=draft_input.draft_probs` -> the `draft_probs` argument). Zero divergent lines are merged.
2. **Relocation proof**: the committed `build_eagle_verify_input` body is AST-equivalent to the eagle source block verbatim (the only textual drift is black reflow after dedent).

Notes:

- The single real difference between the two workers — where `draft_probs` comes from (this round's `draft_forward` output vs. the ones carried on the draft input) — is expressed as a call-site argument, not a branch.
- Zero behavior change; frozen-KV MTP's draft tail differs materially (no verify-buffer fill, returns `FrozenKVMTPVerifyInput`) and is intentionally not folded in.
- The topk1-fastpath unit test's `build_tree_kernel_efficient` patch target moves to `eagle_worker_common` (the name it is now looked up from).
- compile + ruff (F401/F821) clean across `speculative/`.

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29454493130](https://github.com/sgl-project/sglang/actions/runs/29454493130)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29454493089](https://github.com/sgl-project/sglang/actions/runs/29454493089)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
