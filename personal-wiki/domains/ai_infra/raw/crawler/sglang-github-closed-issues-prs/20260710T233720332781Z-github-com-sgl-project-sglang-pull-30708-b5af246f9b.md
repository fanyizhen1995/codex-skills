---
source_id: sglang-github-closed-issues-prs
title: '[style] Extract init-static values in forward path'
canonical_url: https://github.com/sgl-project/sglang/pull/30708
captured_at: '2026-07-10T23:37:20.332781+00:00'
content_hash: b5af246f9b6736621dcb84c9aadd129b53773e6d5bf81821d8eb74fee0bab1a7
---
# [style] Extract init-static values in forward path

URL: https://github.com/sgl-project/sglang/pull/30708
State: closed
Labels: run-ci
Closed at: 2026-07-10T02:35:00Z
Merged at: 2026-07-10T02:35:00Z

Follows the new **"Extract init-static values at construction"** rule (#30701): when a derived value's inputs are frozen for the object's lifetime, compute it once in `__init__` and read the attribute instead of re-deriving in hot paths.

This PR covers the **model runner + attention + logits forward path**.

## Changes

**`hybrid_attn_backend.py`**
- Cache `spec_attn_is_decode` / `spec_attn_is_prefill`; replaces 3 `speculative_attention_mode == "..."` comparisons. `_select_backend` runs **once per attention layer per forward**, so this is the hottest fix in this PR.

**`model_runner.py`**
- Replace the stray duplicate `self.server_args.elastic_ep_backend is not None` in `forward()` with the already-cached `self.enable_elastic_ep` (set in `__init__`, used correctly 40 lines above).

**`base_runner.py` + `eager_runner.py` + `decode_cuda_graph_runner.py`**
- Hoist `enable_pdmux` into `BaseRunner.__init__` (replaces 4 `eager_runner` reads); drop the now-redundant duplicate in `DecodeCudaGraphRunner`
- Hoist `enable_return_hidden_states` into `BaseRunner.__init__` (replaces reads in decode + cpu graph runners)

**`cpu_graph_runner.py`**
- Cache `enable_return_hidden_states` (`CPUGraphRunner` does not inherit `BaseRunner`)

**`logits_processor.py` + `forward_batch_info.py`**
- Cache `rl_on_policy_target` in `LogitsProcessor.__init__` (mirrors `Sampler`); hoist to a local in `_compute_mrope_positions` to kill **per-sequence** `get_server_args()` calls inside the `for batch_idx in range(batch_size)` loop.

## Verification
All changes are **pure attribute-read substitutions** (no logic change). Verified by count-based equivalence + AST parse + ruff/black/isort/codespell all pass.













<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29058383466](https://github.com/sgl-project/sglang/actions/runs/29058383466)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29058383244](https://github.com/sgl-project/sglang/actions/runs/29058383244)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
