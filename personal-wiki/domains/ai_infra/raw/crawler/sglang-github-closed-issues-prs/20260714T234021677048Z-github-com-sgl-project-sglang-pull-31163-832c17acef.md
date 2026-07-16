---
source_id: sglang-github-closed-issues-prs
title: Extract per-architecture KV-cache pool builders into KVCacheConfigurator
canonical_url: https://github.com/sgl-project/sglang/pull/31163
captured_at: '2026-07-14T23:40:21.677048+00:00'
content_hash: 832c17acef6fb6dad8e242c9e4c71c53721a46686ae1c8b0d6e9b067219a3982
---
# Extract per-architecture KV-cache pool builders into KVCacheConfigurator

URL: https://github.com/sgl-project/sglang/pull/31163
State: closed
Labels: 
Closed at: 2026-07-14T08:02:10Z
Merged at: 2026-07-14T08:02:10Z

### mrc-kv-cache-configurator-pools(kvc-req-pools-prep,non_mechanical_provable): Stage req-pool branches for certifiable extraction

Remove the walrus binding (config := self.mambaish_config -> self.mambaish_config,
config.X -> self.mambaish_config.X), inline the shared max_spec_draft_tokens local as
self.server_args.max_speculative_num_draft_tokens, and duplicate the shared disaggregation
decode import down into each branch, so each req-pool block is a verbatim body ready for
extract_function.

### mrc-kv-cache-configurator-pools(kvc-extract-build-hybrid-mamba-decode-req-pool,mechanical_provable): Extract _build_hybrid_mamba_decode_req_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-decode-req-pool,mechanical_provable): Extract _build_decode_req_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-hybrid-req-pool,mechanical_provable): Extract _build_hybrid_req_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-default-req-pool,mechanical_provable): Extract _build_default_req_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-dsv4-kv-pool,mechanical_provable): Extract _build_dsv4_kv_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-oot-dsa-kv-pool,mechanical_provable): Extract _build_oot_dsa_kv_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-oot-mla-kv-pool,mechanical_provable): Extract _build_oot_mla_kv_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-oot-mha-kv-pool,mechanical_provable): Extract _build_oot_mha_kv_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-ascend-swa-kv-pool,mechanical_provable): Extract _build_ascend_swa_kv_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-ascend-mla-kv-pool,mechanical_provable): Extract _build_ascend_mla_kv_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-ascend-mha-kv-pool,mechanical_provable): Extract _build_ascend_mha_kv_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-dsa-kv-pool,mechanical_provable): Extract _build_dsa_kv_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-mla-fp4-kv-pool,mechanical_provable): Extract _build_mla_fp4_kv_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-mla-kv-pool,mechanical_provable): Extract _build_mla_kv_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-hybrid-swa-kv-pool,mechanical_provable): Extract _build_hybrid_swa_kv_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-minimax-sparse-kv-pool,mechanical_provable): Extract _build_minimax_sparse_kv_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-hybrid-linear-prep,non_mechanical_provable): Resolve the walrus binding in the hybrid-linear branch for certifiable extraction

Replace elif config := self.mambaish_config with elif self.mambaish_config and
config.full_attention_layer_ids with self.mambaish_config.full_attention_layer_ids, so the
block is a verbatim body ready for extract_function.

### mrc-kv-cache-configurator-pools(kvc-extract-build-hybrid-linear-kv-pool,mechanical_provable): Extract _build_hybrid_linear_kv_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-mha-fp4-kv-pool,mechanical_provable): Extract _build_mha_fp4_kv_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-mha-kv-pool,mechanical_provable): Extract _build_mha_kv_pool from _init_pools

### mrc-kv-cache-configurator-pools(kvc-extract-build-token-to-kv-pool,mechanical_provable): Wrap the token_to_kv_pool dispatch as a method

### mrc-kv-cache-configurator-pools(kvc-extract-build-req-to-token-pool,mechanical_provable): Wrap the req_to_token_pool block as a method

### mrc-kv-cache-configurator-pools(kvc-extract-build-token-to-kv-pool-allocator,mechanical_provable): Wrap the allocator block as a method

### mrc-kv-cache-configurator-pools(kvc-reorder-req-wrap,mechanical_provable): Move _build_req_to_token_pool above the req-pool helpers

### mrc-kv-cache-configurator-pools(kvc-reorder-kv-wrap,mechanical_provable): Move _build_token_to_kv_pool above the kv-pool helpers

### mrc-kv-cache-configurator-pools(kvc-extract-derive-pool-sizes,non_mechanical_provable): Extract _derive_pool_sizes + introduce _PoolSizes dataclass

Pull the 30 lines of pool-size derivation from configure() into a private
_derive_pool_sizes method, with the 9 derived scalars packaged in a new
private _PoolSizes dataclass (frozen/slots/kw_only). _init_pools signature
collapses from 9 size kwargs + 2 pre-injection kwargs to sizes:_PoolSizes
+ the 2 pre-injection kwargs; body uses sizes.X directly at each helper
call site (no top-of-body unpack into 9 locals).

configure() now reads as: resolve config -> derive sizes -> init pools ->
log -> build result.

PR-Title: Introduce KVCacheConfigurator and drop the KV-cache mixin

### mrc-kv-cache-configurator-pools(kvc-dissolve-init-memory-pool,non_mechanical_provable): Route alloc_memory_pool through KVCacheConfigurator.configure directly

The init_memory_pool result-unpacking delegate dissolves into
alloc_memory_pool; the mixin is now an empty shell.

### mrc-kv-cache-configurator-pools(kvc-drop-mixin-inheritance,non_mechanical_provable): Drop the now-empty ModelRunnerKVCacheMixin

Every member has migrated to KVCacheConfigurator / kv_pool_runtime /
ModelRunner; delete the empty shell and the inheritance edge.

### mrc-kv-cache-configurator-pools(postpare,non_mechanical_provable): Complete KVCacheConfigurator for the current upstream KV-cache stack

Add the pp_group/model_dtype/sliding_window_size/spec_aux_config stand-in
fields + construction (read by pool_configurator through the kvc handle),
restore the linear_replayssm kwargs in _hybrid_req_pool, route
pool_configurator through mr.model_dtype / mr.ps.pp_size, and update the
pool-configurator unit-test fixture accordingly.

### mrc-kv-cache-configurator-pools(layer-info,non_mechanical_provable): Consolidate KVCacheConfigurator layer fields into a single layer_info

Replace the flat start_layer/end_layer/num_effective_layers fields with one
layer_info: ModelLayerInfo field; internal reads go through layer_info.*, fix
the mixed-spelling reads in pool_configurator, and drop the dead
dflash_draft_num_layers field.

### mrc-kv-cache-configurator-pools(kvc-restore-override-labels,non_mechanical_provable): Keep the base server_args.override labels for the mamba-cache overrides

### mrc-kv-cache-configurator-pools(kvc-derive-arch-configs,non_mechanical_provable): Derive mambaish_config/hybrid_gdn_config in __post_init__ instead of taking them as constructor args

### mrc-kv-cache-configurator-pools(rename-pool-configurator-mr,non_mechanical_provable): Rename mr to kvc in pool_configurator

Use the full model_runner name (not the mr alias) in pool_configurator for
consistency with the extracted model-runner component modules.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29316588246](https://github.com/sgl-project/sglang/actions/runs/29316588246)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29316587963](https://github.com/sgl-project/sglang/actions/runs/29316587963)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
