---
source_id: sglang-github-closed-issues-prs
title: Extract load_model helpers into a load_model_utils module
canonical_url: https://github.com/sgl-project/sglang/pull/31155
captured_at: '2026-07-14T23:40:21.678872+00:00'
content_hash: 10a1bac12137e50f8ab8c71c3517efb35edddc5a32ba3cfaaf1b6e9564e8f6bb
---
# Extract load_model helpers into a load_model_utils module

URL: https://github.com/sgl-project/sglang/pull/31155
State: closed
Labels: 
Closed at: 2026-07-14T07:58:40Z
Merged at: 2026-07-14T07:58:40Z

### mrc-load-model-utils(loadmodel-extract-downgrade-dtype,non_mechanical_provable): Extract _maybe_downgrade_dtype_for_legacy_gpu

### mrc-load-model-utils(loadmodel-extract-build-load-config,non_mechanical_provable): Extract _build_load_config -> LoadConfig

### mrc-load-model-utils(loadmodel-extract-trigger-remote-nccl,non_mechanical_provable): Extract _maybe_trigger_remote_instance_nccl_send_group

### mrc-load-model-utils(loadmodel-extract-load-with-memory-saver,non_mechanical_provable): Extract _load_model_with_memory_saver

### mrc-load-model-utils(loadmodel-extract-post-load-derivations,non_mechanical_provable): Extract _load_kv_cache_scales + _resolve_sliding_window_size

### mrc-load-model-utils(loadmodel-extract-debug-tensor-dump,non_mechanical_provable): Extract _maybe_register_debug_tensor_dump_hook

### mrc-load-model-utils(loadmodel-extract-dist-barrier,non_mechanical_provable): Extract _dist_barrier_after_load

### mrc-load-model-utils(extract-downgrade-dtype-prep,non_mechanical_provable): inline maybe_downgrade_dtype_for_legacy_gpu into model_runner before move

### mrc-load-model-utils(extract-downgrade-dtype-move,mechanical_provable): move maybe_downgrade_dtype_for_legacy_gpu to load_model_utils module (cut+paste)

### mrc-load-model-utils(extract-trigger-remote-nccl-prep,non_mechanical_provable): de-self _maybe_trigger_remote_instance_nccl_send_group to @staticmethod

### mrc-load-model-utils(extract-trigger-remote-nccl-move,mechanical_provable): move maybe_trigger_remote_instance_nccl_send_group to load_model_utils module (cut+paste)

### mrc-load-model-utils(extract-load-kv-cache-scales-prep,non_mechanical_provable): de-self _load_kv_cache_scales to @staticmethod

### mrc-load-model-utils(extract-load-kv-cache-scales-move,mechanical_provable): move load_kv_cache_scales to load_model_utils module (cut+paste)

### mrc-load-model-utils(extract-resolve-sliding-window-prep,non_mechanical_provable): de-self _resolve_sliding_window_size to @staticmethod

### mrc-load-model-utils(extract-resolve-sliding-window-move,mechanical_provable): move resolve_sliding_window_size to load_model_utils module

### mrc-load-model-utils(extract-debug-tensor-dump-hook-prep,non_mechanical_provable): de-self _maybe_register_debug_tensor_dump_hook to @staticmethod

### mrc-load-model-utils(extract-debug-tensor-dump-hook-move,mechanical_provable): move maybe_register_debug_tensor_dump_hook to load_model_utils module (cut+paste)

PR-Title: Extract load-model helpers into load_model_utils

### mrc-load-model-utils(online-quant-report-prep,non_mechanical_provable): Extract online-quantization reporting into a de-self'd report_online_quantization @staticmethod in place

The inline reporting block in load_model becomes a kwargs @staticmethod next
to it; the block is replaced by the class-qualified call.

### mrc-load-model-utils(online-quant-report-move,mechanical_provable): Move report_online_quantization to load_model_utils (cut+paste)

### mrc-load-model-utils(load-model-fns-rename,non_mechanical_provable): Privacy-flip the three load_model helpers to their public move names

_build_load_config / _load_model_with_memory_saver / _dist_barrier_after_load
become build_load_config / load_model_with_memory_saver /
dist_barrier_after_load in place, ahead of the module move.

### mrc-load-model-utils(load-model-fns-inplace-prep,non_mechanical_provable): Prep build_load_config / load_model_with_memory_saver / dist_barrier_after_load for extraction: @staticmethod + kwargs + LoadedModel

De-self the three helpers in place as kwargs @staticmethods (bodies stay at
their original class positions); load_model calls them class-qualified and
unpacks the LoadedModel result. Stage the LoadedModel struct and the header
additions in load_model_utils so the moves land in an existing module.

### mrc-load-model-utils(load-model-fns-move,mechanical_provable): Move build_load_config / load_model_with_memory_saver / dist_barrier_after_load + UNBALANCED_MODEL_LOADING_TIMEOUT_S to load_model_utils (cut+paste)







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29316378028](https://github.com/sgl-project/sglang/actions/runs/29316378028)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29316377855](https://github.com/sgl-project/sglang/actions/runs/29316377855)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
