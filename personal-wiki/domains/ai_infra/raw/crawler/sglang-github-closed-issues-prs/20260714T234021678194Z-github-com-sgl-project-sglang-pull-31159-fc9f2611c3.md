---
source_id: sglang-github-closed-issues-prs
title: Extract MoE/EP setup into a moe_ep_setup module
canonical_url: https://github.com/sgl-project/sglang/pull/31159
captured_at: '2026-07-14T23:40:21.678194+00:00'
content_hash: fc9f2611c3a54ba8ad10a308b8d47ce98bece794fa7b2dbe4767b3f5ac1f9b0a
---
# Extract MoE/EP setup into a moe_ep_setup module

URL: https://github.com/sgl-project/sglang/pull/31159
State: closed
Labels: 
Closed at: 2026-07-14T08:00:25Z
Merged at: 2026-07-14T08:00:25Z

### mrc-moe-ep-setup(extract-prepare-moe-topk-prep,non_mechanical_provable): inline prepare_moe_topk into model_runner before move

### mrc-moe-ep-setup(extract-prepare-moe-topk-move,mechanical_provable): move prepare_moe_topk to moe_ep_setup module

### mrc-moe-ep-setup(extract-prepare-moe-topk-postpare,non_mechanical_provable): black-collapse two now-shorter Waterfill statements

After the upstream #27350 Waterfill rename shortened two strings in
prepare_moe_topk (the ValueError message and the log_info_on_rank0 call), they
fit on one line, so black collapses them. Applied as a postpare after the
cut+paste move so the move itself stays byte-faithful.

### mrc-moe-ep-setup(extract-init-lplb-solvers-prep,non_mechanical_provable): de-self _init_lplb_solvers to @staticmethod init_lplb_solvers

### mrc-moe-ep-setup(extract-init-lplb-solvers-move,non_mechanical_provable): Move init_lplb_solvers to moe_ep_setup module and repoint the EPLBManager callable

### mrc-moe-ep-setup(extract-quant-moe-checks-prep,non_mechanical_provable): de-self check_quantized_moe_compatibility to @staticmethod

### mrc-moe-ep-setup(extract-quant-moe-checks-move,non_mechanical_provable): Move check_quantized_moe_compatibility and its _use_aiter constant to moe_ep_setup module







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29316481647](https://github.com/sgl-project/sglang/actions/runs/29316481647)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29316481363](https://github.com/sgl-project/sglang/actions/runs/29316481363)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
