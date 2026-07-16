---
source_id: sglang-github-closed-issues-prs
title: Extract spec aux-hidden-state resolution into a module
canonical_url: https://github.com/sgl-project/sglang/pull/31157
captured_at: '2026-07-14T23:40:21.678649+00:00'
content_hash: 6a6c01c55d551084ef3c3ee0548921b3242c9ba46d7dfba67df5466adfed1799
---
# Extract spec aux-hidden-state resolution into a module

URL: https://github.com/sgl-project/sglang/pull/31157
State: closed
Labels: 
Closed at: 2026-07-14T07:59:35Z
Merged at: 2026-07-14T07:59:35Z

### mrc-spec-aux-hidden-state(extract-spec-aux-hidden-state-prep,non_mechanical_provable): inline resolve_spec_aux_hidden_state_config into model_runner before move

### mrc-spec-aux-hidden-state(extract-spec-aux-hidden-state-move,mechanical_provable): move spec aux-hidden-state resolution to spec_aux_hidden_state module (cut+paste)

### mrc-spec-aux-hidden-state(extract-per-algorithm-helpers-from-resolve-spec,non_mechanical_provable): Extract per-algorithm helpers from resolve_spec_aux_hidden_state_config

Split the eagle and dflash branches into _resolve_eagle_aux_hidden_state and
_resolve_dflash_aux_hidden_state; the orchestrator now just constructs the
config and calls both. Bodies are unchanged.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29316432870](https://github.com/sgl-project/sglang/actions/runs/29316432870)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29316432712](https://github.com/sgl-project/sglang/actions/runs/29316432712)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
