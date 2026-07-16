---
source_id: sglang-github-closed-issues-prs
title: Extract layer-index setup into a module
canonical_url: https://github.com/sgl-project/sglang/pull/31156
captured_at: '2026-07-14T23:40:21.678426+00:00'
content_hash: 2234f47cf55217667c6081ea8677d26f17bf3745c0062c19c5d8dbdc14cfef08
---
# Extract layer-index setup into a module

URL: https://github.com/sgl-project/sglang/pull/31156
State: closed
Labels: apple-silicon
Closed at: 2026-07-14T07:59:08Z
Merged at: 2026-07-14T07:59:08Z

### mrc-layer-setup(small-funcs-prep,non_mechanical_provable): Stage PPLayerRange + the three layer-setup helpers as de-self'd free functions in place and rewire initialize

### mrc-layer-setup(small-funcs-move,mechanical_provable): Extract PPLayerRange / compute_model_num_layers / resolve_pp_layer_range / assert_pp_mtp_compat to layer_setup.py (cut+paste)

### mrc-layer-setup(mrc-layer-setup-reorder-adjust-hybrid-swa,non_mechanical_provable): Move adjust_hybrid_swa call below loop_num + assert (functionally equivalent, prep for orchestrator wrap)

### mrc-layer-setup(mrc-layer-setup-extract-resolve-layer-indices-orchestrator,non_mechanical_provable): Wrap compute/pp_range/loop_num/assert into resolve_layer_indices; privatize sub-helpers

### mrc-layer-setup(adjust-hybrid-swa-prep,non_mechanical_provable): Parameterize adjust_hybrid_swa_layers_for_pp (self.X -> kwargs) into a free function in place

### mrc-layer-setup(adjust-hybrid-swa-move,mechanical_provable): Move adjust_hybrid_swa_layer_ids to layer_setup (cut+paste)

### mrc-layer-setup(attention-moe-layers-prep,non_mechanical_provable): Extract attention/moe layer collection into a de-self'd compute_attention_and_moe_layers free function in place

### mrc-layer-setup(attention-moe-layers-move,mechanical_provable): Move compute_attention_and_moe_layers to layer_setup (cut+paste)







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29316402486](https://github.com/sgl-project/sglang/actions/runs/29316402486)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29316402322](https://github.com/sgl-project/sglang/actions/runs/29316402322)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
