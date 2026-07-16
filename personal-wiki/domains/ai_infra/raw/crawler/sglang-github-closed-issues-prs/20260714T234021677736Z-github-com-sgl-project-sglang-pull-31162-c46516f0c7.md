---
source_id: sglang-github-closed-issues-prs
title: Introduce KVCacheConfigurator and migrate KV-cache config logic
canonical_url: https://github.com/sgl-project/sglang/pull/31162
captured_at: '2026-07-14T23:40:21.677736+00:00'
content_hash: c46516f0c7cf24d2c9186a2b9fef6f78da4194820caed1e5bf4c1eaa0ec9d33d
---
# Introduce KVCacheConfigurator and migrate KV-cache config logic

URL: https://github.com/sgl-project/sglang/pull/31162
State: closed
Labels: 
Closed at: 2026-07-14T08:01:46Z
Merged at: 2026-07-14T08:01:46Z

### mrc-kv-cache-configurator-core(kvc-introduce-skeleton,non_mechanical_provable): Introduce KVCacheConfigurator + KVCacheConfigResult skeletons

### mrc-kv-cache-configurator-core(kvc-extract-mla-dim-prep,non_mechanical_provable): Prep calculate_mla_kv_cache_dim for extraction

### mrc-kv-cache-configurator-core(kvc-extract-mla-dim-move,mechanical_provable): Move calculate_mla_kv_cache_dim to mem_cache.kv_cache_configurator (cut+paste)

### mrc-kv-cache-configurator-core(kvc-move-dsv4-compress-dtypes,non_mechanical_provable): Move _get_dsv4_compress_state_dtypes to kv_cache_configurator (cut+paste)

### mrc-kv-cache-configurator-core(kvc-move-lazy-compaction-gate,non_mechanical_provable): Move _should_enable_lazy_compaction to kv_cache_configurator (cut+paste)

Single-function module-level cut+paste; labeled non-mechanical only because
the generator cannot express the insertion position before the TYPE_CHECKING
block (same limitation class as kvc-move-dsv4-compress-dtypes). The mixin-side
envs import becomes unused and is dropped.

### mrc-kv-cache-configurator-core(kvc-move-mamba-ratio-constants,non_mechanical_provable): Move the MAMBA_CACHE ratio constants to kv_cache_configurator (cut+paste)

Definitions move to the configurator module header; the mixin imports them
until _calculate_mamba_ratio migrates. Labeled non-mechanical only because the
generator cannot express the insertion position before the TYPE_CHECKING block
(same limitation class as kvc-move-dsv4-compress-dtypes).

### mrc-kv-cache-configurator-core(kvc-migrate-calculate-mamba-ratio,mechanical_provable): Migrate _calculate_mamba_ratio onto KVCacheConfigurator, leaving a forwarding delegate (cut+paste)

### mrc-kv-cache-configurator-core(kvc-handle-max-mamba-cache-prep,non_mechanical_provable): Reshape handle_max_mamba_cache to its KVCacheConfigurator form in place

Privacy-flip to _handle_max_mamba_cache (caller updated), read mambaish_config
off self, unify the override labels to kv_cache_configurator.max_mamba_cache_size,
and route the per-DP divisors through ps.attn_dp_size. Add the KVCacheConfigurator
ps field + construction wiring it will need after the move.

### mrc-kv-cache-configurator-core(kvc-migrate-handle-max-mamba-cache,mechanical_provable): Migrate _handle_max_mamba_cache onto KVCacheConfigurator, leaving a forwarding delegate (cut+paste)

### mrc-kv-cache-configurator-core(kvc-apply-token-constraints-prep,non_mechanical_provable): Read pp_size via server_args in _apply_token_constraints (KVCacheConfigurator form)

### mrc-kv-cache-configurator-core(kvc-migrate-apply-token-constraints,mechanical_provable): Migrate _apply_token_constraints onto KVCacheConfigurator, leaving a forwarding delegate (cut+paste)

### mrc-kv-cache-configurator-core(kvc-resolve-max-num-reqs-prep,non_mechanical_provable): Reshape _resolve_max_num_reqs to its KVCacheConfigurator form in place

Privacy-flip to resolve_max_num_reqs (callers + flashinfer comment updated),
divisor via ps.attn_dp_size, read mambaish_config off self.

### mrc-kv-cache-configurator-core(kvc-migrate-resolve-max-num-reqs,mechanical_provable): Migrate resolve_max_num_reqs onto KVCacheConfigurator, leaving a forwarding delegate (cut+paste)

### mrc-kv-cache-configurator-core(kvc-config-from-budget-prep,non_mechanical_provable): Reshape _config_from_budget to its KVCacheConfigurator form in place

Privacy-flip to config_from_budget (callers updated); page_size read via
server_args.

### mrc-kv-cache-configurator-core(kvc-migrate-config-from-budget,mechanical_provable): Migrate config_from_budget onto KVCacheConfigurator, leaving a forwarding delegate (cut+paste)

### mrc-kv-cache-configurator-core(kvc-profile-available-bytes-prep,non_mechanical_provable): Reshape _profile_available_bytes to its KVCacheConfigurator form in place

mem_fraction_static read via server_args; mambaish_config read off self. Add
the KVCacheConfigurator post_capture_kv_active field + construction wiring.

### mrc-kv-cache-configurator-core(kvc-migrate-profile-available-bytes,mechanical_provable): Migrate _profile_available_bytes onto KVCacheConfigurator, leaving a forwarding delegate (cut+paste)

### mrc-kv-cache-configurator-core(kvc-migrate-resolve-memory-pool-config,mechanical_provable): Migrate _resolve_memory_pool_config onto KVCacheConfigurator, leaving a forwarding delegate (cut+paste)

### mrc-kv-cache-configurator-core(kvc-validate-prefill-only-prep,non_mechanical_provable): Read mambaish_config off self in _validate_prefill_only_disable_kv_cache_pool_family (KVCacheConfigurator form)

### mrc-kv-cache-configurator-core(kvc-migrate-validate-prefill-only,mechanical_provable): Migrate _validate_prefill_only_disable_kv_cache_pool_family onto KVCacheConfigurator, leaving a forwarding delegate (cut+paste)

### mrc-kv-cache-configurator-core(kvc-unified-mamba-prep,non_mechanical_provable): Reshape _init_unified_mamba_pools to its KVCacheConfigurator form in place

Bundle-returning kwargs signature (max_num_reqs + max_total_num_tokens);
the fast-path caller unpacks the bundle onto ModelRunner. Add the
KVCacheConfigurator page_size / forward_stream fields + construction and the
layer_info bridge property.

### mrc-kv-cache-configurator-core(kvc-migrate-unified-mamba,mechanical_provable): Migrate _init_unified_mamba_pools onto KVCacheConfigurator, leaving a forwarding delegate (cut+paste)

### mrc-kv-cache-configurator-core(kvc-unified-swa-prep,non_mechanical_provable): Reshape _init_unified_swa_pools to its KVCacheConfigurator form in place

Bundle-returning kwargs signature (max_num_reqs + full/swa token caps); the
fast-path caller unpacks the bundle onto ModelRunner.

### mrc-kv-cache-configurator-core(kvc-migrate-unified-swa,mechanical_provable): Migrate _init_unified_swa_pools onto KVCacheConfigurator, leaving a forwarding delegate (cut+paste)

### mrc-kv-cache-configurator-core(kv-pool-runtime-prep,non_mechanical_provable): Prep the post-capture KV-resize pieces for extraction in place

post_capture_kv_active becomes the is_post_capture_kv_active kwargs free
function feeding the KVCacheConfigurator ctor; post_capture_resize_kv_pool
splits into the field-writing wrapper plus compute_post_capture_kv_resize
returning the staged PostCaptureKVResize struct. Stage the kv_pool_runtime
module header.

### mrc-kv-cache-configurator-core(kv-pool-runtime-move,mechanical_provable): Move is_post_capture_kv_active / PostCaptureKVResize / compute_post_capture_kv_resize to model_runner_components/kv_pool_runtime.py (cut+paste)

### mrc-kv-cache-configurator-core(kv-pool-runtime-wrapper-move,mechanical_provable): Move the post_capture_resize_kv_pool wrapper from the mixin onto ModelRunner (cut+paste)

### mrc-kv-cache-configurator-core(kvc-init-pools-prep,non_mechanical_provable): Reshape _init_pools to its KVCacheConfigurator form in place

12-kwarg signature (sizes + injected pools), self-state writes -> locals in
_apply_memory_pool_config, _InitializedPools bundle return. The unified-pool
fast path stays at the top of _init_pools, now returning the bundle. Stage the
_InitializedPools struct in the configurator module.

### mrc-kv-cache-configurator-core(kvc-migrate-init-pools,mechanical_provable): Migrate _init_pools onto KVCacheConfigurator, leaving a forwarding delegate (cut+paste)

### mrc-kv-cache-configurator-core(kvc-migrate-configure,non_mechanical_provable): Synthesize KVCacheConfigurator.configure; reduce the mixin to the init_memory_pool delegate

configure = resolve config -> sizes -> _init_pools bundle -> log -> result
(KVCacheConfigResult gains unified_memory_pool). The mixin keeps only the
init_memory_pool result-unpacking delegate; the dead forwarding delegates are
dropped. Also define the _is_npu module flag the relocated _init_pools body
reads (missed in kvc-migrate-init-pools).

### mrc-kv-cache-configurator-core(kvc-complete-module-header,non_mechanical_provable): Complete the configurator module header

Add the imports + logger the migrated method bodies read (memory pools,
allocators, SWA/hisparse/DSV4 pool classes, platform + parallel-state
helpers, math). The migration moves carried bodies only; this closes the
within-PR import gap in one place.

### mrc-kv-cache-configurator-core(kvc-drop-stale-self-annotations,non_mechanical_provable): Drop the stale self: ModelRunner annotations on migrated KVCacheConfigurator methods







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29316564440](https://github.com/sgl-project/sglang/actions/runs/29316564440)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29316564209](https://github.com/sgl-project/sglang/actions/runs/29316564209)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
