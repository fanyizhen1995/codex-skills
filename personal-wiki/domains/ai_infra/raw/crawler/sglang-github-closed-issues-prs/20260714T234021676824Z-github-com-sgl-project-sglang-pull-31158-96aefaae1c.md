---
source_id: sglang-github-closed-issues-prs
title: Extract small single-function helpers into modules
canonical_url: https://github.com/sgl-project/sglang/pull/31158
captured_at: '2026-07-14T23:40:21.676824+00:00'
content_hash: 96aefaae1cdb6a75ac080f9a26b250ad3506676ca61e29fd8c0fc37bcb3ab9c6
---
# Extract small single-function helpers into modules

URL: https://github.com/sgl-project/sglang/pull/31158
State: closed
Labels: 
Closed at: 2026-07-14T08:00:01Z
Merged at: 2026-07-14T08:00:01Z

### mrc-misc-fn-modules(extract-msprobe-prep,non_mechanical_provable): inline create_msprobe_debugger into model_runner before move

### mrc-misc-fn-modules(extract-msprobe-move,mechanical_provable): move msprobe debugger init to msprobe module (cut+paste)

### mrc-misc-fn-modules(msprobe-wrapper-postpare,non_mechanical_provable): Requalify the create_msprobe_debugger wrapper call through the misc_utils module import

### mrc-misc-fn-modules(extract-chunked-prefix-gate-prep,non_mechanical_provable): Extract the chunked-prefix-cache gate into a de-self'd maybe_disable_chunked_prefix_cache free function in place

### mrc-misc-fn-modules(extract-chunked-prefix-gate-move,mechanical_provable): move maybe_disable_chunked_prefix_cache to misc_utils module (cut+paste)

### mrc-misc-fn-modules(chunked-prefix-wrapper-postpare,non_mechanical_provable): Requalify the maybe_disable_chunked_prefix_cache call through the misc_utils module import

### mrc-misc-fn-modules(extract-pp-proxy-prep,non_mechanical_provable): inline resolve_pp_proxy_topk_size into model_runner before move

### mrc-misc-fn-modules(extract-pp-proxy-move,mechanical_provable): move pp-proxy topk-size resolution to misc_utils module (cut+paste)

### mrc-misc-fn-modules(pp-proxy-wrapper-postpare,non_mechanical_provable): Requalify the resolve_pp_proxy_topk_size wrapper call through the misc_utils module import

### mrc-misc-fn-modules(extract-expert-location-src-rank-prep,non_mechanical_provable): inline get_healthy_expert_location_src_rank into model_runner before move

### mrc-misc-fn-modules(extract-expert-location-src-rank-move,mechanical_provable): move get_healthy_expert_location_src_rank to elastic_ep module (cut+paste)







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29316455681](https://github.com/sgl-project/sglang/actions/runs/29316455681)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29316455500](https://github.com/sgl-project/sglang/actions/runs/29316455500)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
