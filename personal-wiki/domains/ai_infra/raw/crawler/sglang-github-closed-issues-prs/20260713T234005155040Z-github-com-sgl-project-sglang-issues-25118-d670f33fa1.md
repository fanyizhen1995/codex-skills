---
source_id: sglang-github-closed-issues-prs
title: '[Bug] DeepSeek-V4-Flash on MI300x failed with assertion error "assert self.store_dtype
  == torch.uint8"'
canonical_url: https://github.com/sgl-project/sglang/issues/25118
captured_at: '2026-07-13T23:40:05.155040+00:00'
content_hash: d670f33fa1c78bbdf2eeb4412396edd733553facb245e6b587668b21aca8ba68
---
# [Bug] DeepSeek-V4-Flash on MI300x failed with assertion error "assert self.store_dtype == torch.uint8"

URL: https://github.com/sgl-project/sglang/issues/25118
State: closed
Labels: inactive
Closed at: 2026-07-13T00:36:22Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

Tried to launch deepseek-v4-flash on MI300x following the instructions from this RP

https://github.com/sgl-project/sglang/pull/23608

failed with assertion error "assert self.store_dtype == torch.uint8"

### Reproduction

Docker launch command:
```
docker run -it -v /eph/nvme/models:/eph/nvme/models --ipc host --network host --shm-size 32G --device /dev/kfd --device /dev/dri --group-add video --cap-add SYS_PTRACE -e HSA_NO_SCRATCH_RECLAIM=1 --privileged rocm/sgl-d
ev:rocm720-mi30x-339e36e-20260512-DSv4 bash
```

```
# export CUDA_VISIBLE_DEVICES=0,1,2,3

export SGLANG_OPT_USE_FUSED_COMPRESS=false #use PyTorch implemented compressor
export SGLANG_OPT_USE_OLD_COMPRESSOR=true #use old compressor
export SGLANG_OPT_USE_TILELANG_SWA_PREPARE=false #use old prepare
export SGLANG_OPT_USE_JIT_KERNEL_FUSED_TOPK=false #use old topk
export SGLANG_OPT_USE_FUSED_HASH_TOPK=false #AMD: hash_topk JIT needs CUDA toolchain

export SGLANG_HACK_FLASHMLA_BACKEND=torch
export SGLANG_OPT_DEEPGEMM_HC_PRENORM=false #use old prenorm

export SGLANG_OPT_USE_TILELANG_MHC_PRE=false #use torch hc_pre
export SGLANG_OPT_USE_TILELANG_MHC_POST=false #use torch hc_post

export SGLANG_ENABLE_THINKING=1
export SGLANG_USE_AITER=1
export SGLANG_USE_ROCM700A=1
export SGLANG_TOPK_TRANSFORM_512_TORCH=1
export SGLANG_FP8_PAGED_MQA_LOGITS_TORCH=1

export SGLANG_DSV4_FP4_EXPERTS=false

export SGLANG_OPT_DPSK_V4_RADIX=0
export SGLANG_OPT_USE_OVERLAP_STORE_CACHE=false #non-radix backend has no store_cache method
export SGLANG_OPT_USE_FUSED_STORE_CACHE=false #fused_store_cache JIT needs CUDA toolchain

export SGLANG_FORCE_TRITON_MOE_FP8=1  # this is required to apply swiglu_limit clamp in fused_moe_triton
root@mi300-hpc-image-06:/eph/nvme/models# python3 -m sglang.launch_server \
--model-path /eph/nvme/models/DeepSeek-V4-Flash-FP8 \
--trust-remote-code \
--tp 4 \
--dp 4 \
--enable-dp-attention \
--disable-radix-cache \
--attention-backend compressed \
--max-running-request 256 \
--page-size 256 \
--chunked-prefill-size 8192 \
--port 30010 \
--disable-shared-experts-fusion \
--disable-cuda-graph \
--tool-call-parser deepseekv4 \
--reasoning-parser deepseek-v4
/sgl-workspace/sglang/python/sglang/launch_server.py:54: UserWarning: 'python -m sglang.launch_server' is still supported, but 'sglang serve' is the recommended entrypoint.
  Example: sglang serve --model-path <model> [options]
  warnings.warn(
[aiter] import [module_aiter_core] under /sgl-workspace/aiter/aiter/jit/module_aiter_core.so
[aiter] merge tuned file under model_configs/ and configs/ /sgl-workspace/aiter/aiter/configs/bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/dsv3_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/dsv4_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/glm5_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/gptoss_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/kimik2_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/llama405B_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/llama70B_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/qwen32B_bf16_tuned_gemm.csv
[2026-05-13 02:13:58] Hybrid swa model: self.hf_config.architectures=['DeepseekV4ForCausalLM']
[2026-05-13 02:13:58] Setting KV cache dtype to fp8_e4m3 for DeepseekV4ForCausalLM.
[2026-05-13 02:13:58] Use compressed attention backend for DeepseekV4ForCausalLM, setting page_size to 256.
[2026-05-13 02:13:58] DP attention is enabled. The chunked prefill size is adjusted to 2048 to avoid MoE kernel issues.
[2026-05-13 02:13:59] aiter fused_qk_norm_mrope_3d kernel available
[2026-05-13 02:13:59] server_args=ServerArgs(model_path='/eph/nvme/models/DeepSeek-V4-Flash-FP8', tokenizer_path='/eph/nvme/models/DeepSeek-V4-Flash-FP8', tokenizer_mode='auto', tokenizer_backend='huggingface', tokenizer_worker_num=1, skip_tokenizer_init=False, load_format='auto', model_loader_extra_config='{}', trust_remote_code=True, context_length=None, is_embedding=False, enable_multimodal=None, revision=None, model_impl='auto', host='127.0.0.1', port=30010, fastapi_root_path='', grpc_mode=False, skip_server_warmup=False, warmups=None, nccl_port=None, checkpoint_engine_wait_weights_before_ready=False, ssl_keyfile=None, ssl_certfile=None, ssl_ca_certs=None, ssl_keyfile_password=None, enable_ssl_refresh=False, enable_http2=False, dtype='auto', quantization=None, quantization_param_path=None, kv_cache_dtype='fp8_e4m3', enable_fp32_lm_head=False, modelopt_quant=None, modelopt_checkpoint_restore_path=None, modelopt_checkpoint_save_path=None, modelopt_export_path=None, quantize_and_serve=False, rl_quant_profile=None, mem_fraction_static=0.88, max_running_requests=256, max_queued_requests=None, max_total_tokens=None, chunked_prefill_size=2048, enable_dynamic_chunking=False, max_prefill_tokens=16384, prefill_max_requests=None, schedule_policy='fcfs', enable_priority_scheduling=False, disable_priority_preemption=False, default_priority_value=None, abort_on_priority_when_disabled=False, schedule_low_priority_values_first=False, priority_scheduling_preemption_threshold=10, schedule_conservativeness=0.3, page_size=256, swa_full_tokens_ratio=0.8, disable_hybrid_swa_memory=False, radix_eviction_policy='lru', enable_prefill_delayer=False, prefill_delayer_max_delay_passes=30, prefill_delayer_token_usage_low_watermark=None, prefill_delayer_forward_passes_buckets=None, prefill_delayer_wait_seconds_buckets=None, device='cuda', tp_size=4, pp_size=1, pp_max_micro_batch_size=None, pp_async_batch_depth=0, stream_interval=1, batch_notify_size=16, stream_response_default_include_usage=False, incremental_streaming_output=False, enable_streaming_session=False, random_seed=912786775, constrained_json_whitespace_pattern=None, constrained_json_disable_any_whitespace=False, watchdog_timeout=300, soft_watchdog_timeout=None, dist_timeout=None, download_dir=None, model_checksum=None, base_gpu_id=0, gpu_id_step=1, sleep_on_idle=False, use_ray=False, custom_sigquit_handler=None, log_level='info', log_level_http=None, log_requests=False, log_requests_level=2, log_requests_format='text', log_requests_target=None, uvicorn_access_log_exclude_prefixes=[], crash_dump_folder=None, show_time_cost=False, enable_metrics=False, grpc_http_sidecar_port=None, enable_mfu_metrics=False, enable_metrics_for_all_schedulers=False, tokenizer_metrics_custom_labels_header='x-custom-labels', tokenizer_metrics_allowed_custom_labels=None, extra_metric_labels=None, bucket_time_to_first_token=None, bucket_inter_token_latency=None, bucket_e2e_request_latency=None, prompt_tokens_buckets=None, generation_tokens_buckets=None, gc_warning_threshold_secs=0.0, decode_log_interval=40, enable_request_time_stats_logging=False, kv_events_config=None, enable_trace=False, otlp_traces_endpoint='localhost:4317', export_metrics_to_file=False, export_metrics_to_file_dir=None, api_key=None, admin_api_key=None, served_model_name='/eph/nvme/models/DeepSeek-V4-Flash-FP8', weight_version='default', chat_template=None, hf_chat_template_name=None, completion_template=None, file_storage_path='sglang_storage', enable_cache_report=False, reasoning_parser='deepseek-v4', strip_thinking_cache=False, enable_strict_thinking=False, tool_call_parser='deepseekv4', tool_server=None, sampling_defaults='model', dp_size=4, load_balance_method='round_robin', attn_cp_size=1, moe_dp_size=1, dist_init_addr=None, nnodes=1, node_rank=0, json_model_override_args='{}', preferred_sampling_params=None, enable_lora=None, enable_lora_overlap_loading=None, max_lora_rank=None, lora_target_modules=None, lora_paths=None, max_loaded_loras=None, max_loras_per_batch=8, lora_eviction_policy='lru', lora_backend='csgmv', max_lora_chunk_size=16, experts_shared_outer_loras=None, lora_use_virtual_experts=False, lora_strict_loading=False, lora_drain_wait_threshold=0.0, attention_backend='compressed', decode_attention_backend=None, prefill_attention_backend=None, sampling_backend='pytorch', grammar_backend='xgrammar', mm_attention_backend=None, fp8_gemm_runner_backend='auto', fp4_gemm_runner_backend='auto', nsa_prefill_backend=None, nsa_decode_backend=None, disable_flashinfer_autotune=False, mamba_backend='triton', speculative_algorithm=None, speculative_draft_model_path=None, speculative_draft_model_revision=None, speculative_draft_load_format=None, speculative_num_steps=None, speculative_eagle_topk=None, speculative_num_draft_tokens=None, speculative_dflash_block_size=None, speculative_dflash_draft_window_size=None, speculative_accept_threshold_single=1.0, speculative_accept_threshold_acc=1.0, speculative_token_map=None, speculative_attention_mode='prefill', speculative_draft_attention_backend=None, speculative_moe_runner_backend='auto', speculative_moe_a2a_backend=None, speculative_draft_model_quantization=None, speculative_adaptive=False, speculative_adaptive_config=None, speculative_skip_dp_mlp_sync=False, speculative_ngram_min_bfs_breadth=1, speculative_ngram_max_bfs_breadth=10, speculative_ngram_match_type='BFS', speculative_ngram_max_trie_depth=18, speculative_ngram_capacity=10000000, speculative_ngram_external_corpus_path=None, speculative_ngram_external_sam_budget=0, speculative_ngram_external_corpus_max_tokens=10000000, enable_multi_layer_eagle=False, ep_size=1, moe_a2a_backend='none', moe_runner_backend='auto', record_nolora_graph=True, flashinfer_mxfp4_moe_precision='default', enable_flashinfer_allreduce_fusion=False, enforce_disable_flashinfer_allreduce_fusion=False, enable_aiter_allreduce_fusion=False, deepep_mode='auto', ep_num_redundant_experts=0, ep_dispatch_algorithm=None, init_expert_location='trivial', enable_eplb=False, eplb_algorithm='auto', eplb_rebalance_num_iterations=1000, eplb_rebalance_layers_per_chunk=None, eplb_min_rebalancing_utilization_threshold=1.0, expert_distribution_recorder_mode=None, expert_distribution_recorder_buffer_size=1000, enable_expert_distribution_metrics=False, deepep_config=None, moe_dense_tp_size=None, elastic_ep_backend=None, enable_elastic_expert_backup=False, mooncake_ib_device=None, elastic_ep_rejoin=False, max_mamba_cache_size=None, mamba_ssm_dtype=None, mamba_full_memory_ratio=0.9, mamba_scheduler_strategy='no_buffer', mamba_track_interval=256, linear_attn_backend='triton', linear_attn_decode_backend=None, linear_attn_prefill_backend=None, enable_hierarchical_cache=False, hicache_ratio=2.0, hicache_size=0, hicache_write_policy='write_through', hicache_io_backend='kernel', hicache_mem_layout='layer_first', hicache_storage_backend=None, hicache_storage_prefetch_policy='best_effort', hicache_storage_backend_extra_config=None, enable_hisparse=False, hisparse_config=None, enable_lmcache=False, kt_weight_path=None, kt_method='AMXINT4', kt_cpuinfer=None, kt_threadpool_count=2, kt_num_gpu_experts=None, kt_max_deferred_experts_per_token=None, dllm_algorithm=None, dllm_algorithm_config=None, cpu_offload_gb=0, offload_group_size=-1, offload_num_in_group=1, offload_prefetch_step=1, offload_mode='cpu', enable_mis=False, disable_radix_cache=True, cuda_graph_max_bs=512, cuda_graph_bs=[1, 2, 4, 8, 12, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152, 160, 168, 176, 184, 192, 200, 208, 216, 224, 232, 240, 248, 256, 272, 288, 304, 320, 336, 352, 368, 384, 400, 416, 432, 448, 464, 480, 496, 512], disable_cuda_graph=True, disable_cuda_graph_padding=False, enable_breakable_cuda_graph=False, enable_profile_cuda_graph=False, enable_cudagraph_gc=False, debug_cuda_graph=False, enable_layerwise_nvtx_marker=False, enable_nccl_nvls=False, enable_symm_mem=False, disable_flashinfer_cutlass_moe_fp4_allgather=False, enable_tokenizer_batch_encode=False, disable_tokenizer_batch_decode=False, disable_outlines_disk_cache=False, disable_custom_all_reduce=False, enable_mscclpp=False, enable_torch_symm_mem=False, pre_warm_nccl=False, disable_overlap_schedule=False, enable_mixed_chunk=False, enable_dp_attention=True, enable_dp_attention_local_control_broadcast=False, enable_dp_lm_head=False, enable_two_batch_overlap=False, enable_single_batch_overlap=False, tbo_token_distribution_threshold=0.48, enable_torch_compile=False, disable_piecewise_cuda_graph=True, enforce_piecewise_cuda_graph=False, enable_torch_compile_debug_mode=False, torch_compile_max_bs=32, piecewise_cuda_graph_max_tokens=8192, piecewise_cuda_graph_tokens=[4, 8, 12, 16, 20, 24, 28, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 208, 224, 240, 256, 288, 320, 352, 384, 416, 448, 480, 512, 576, 640, 704, 768, 832, 896, 960, 1024, 1280, 1536, 1792, 2048, 2304, 2560, 2816, 3072, 3328, 3584, 3840, 4096, 4608, 5120, 5632, 6144, 6656, 7168, 7680, 8192], piecewise_cuda_graph_compiler='eager', torchao_config='', enable_nan_detection=False, enable_p2p_check=False, triton_attention_reduce_in_fp32=False, triton_attention_num_kv_splits=16, triton_attention_split_tile_size=None, num_continuous_decode_steps=1, delete_ckpt_after_loading=False, enable_memory_saver=False, enable_weights_cpu_backup=False, enable_draft_weights_cpu_backup=False, allow_auto_truncate=False, enable_custom_logit_processor=False, flashinfer_mla_disable_ragged=False, disable_shared_experts_fusion=True, enforce_shared_experts_fusion=False, disable_chunked_prefix_cache=False, disable_fast_image_processor=False, keep_mm_feature_on_device=False, enable_return_hidden_states=False, enable_return_routed_experts=False, enable_return_indexer_topk=False, scheduler_recv_interval=1, numa_node=None, enable_deterministic_inference=False, rl_on_policy_target=None, enable_attn_tp_input_scattered=False, gc_threshold=None, enable_nsa_prefill_context_parallel=False, nsa_prefill_cp_mode='round-robin-split', enable_fused_qk_norm_rope=False, enable_precise_embedding_interpolation=False, enable_fused_moe_sum_all_reduce=False, enable_prefill_context_parallel=False, prefill_cp_mode='in-seq-split', enable_dynamic_batch_tokenizer=False, dynamic_batch_tokenizer_batch_size=32, dynamic_batch_tokenizer_batch_timeout=0.002, debug_tensor_dump_output_folder=None, debug_tensor_dump_layers=None, debug_tensor_dump_input_file=None, debug_tensor_dump_inject=False, disaggregation_mode='null', disaggregation_transfer_backend='mooncake', disaggregation_bootstrap_port=8998, disaggregation_ib_device=None, disaggregation_decode_enable_radix_cache=False, disaggregation_decode_enable_offload_kvcache=False, num_reserved_decode_tokens=512, disaggregation_decode_polling_interval=1, encoder_only=False, language_only=False, encoder_transfer_backend='zmq_to_scheduler', encoder_urls=[], enable_adaptive_dispatch_to_encoder=False, custom_weight_loader=[], weight_loader_disable_mmap=False, weight_loader_prefetch_checkpoints=False, weight_loader_prefetch_num_threads=4, remote_instance_weight_loader_seed_instance_ip=None, remote_instance_weight_loader_seed_instance_service_port=None, remote_instance_weight_loader_send_weights_group_ports=None, remote_instance_weight_loader_backend='nccl', remote_instance_weight_loader_start_seed_via_transfer_engine=False, engine_info_bootstrap_port=6789, modelexpress_config=None, enable_pdmux=False, pdmux_config_path=None, sm_group_num=8, enable_broadcast_mm_inputs_process=False, enable_prefix_mm_cache=False, mm_enable_dp_encoder=False, mm_process_config={}, limit_mm_data_per_request=None, enable_mm_global_cache=False, decrypted_config_file=None, decrypted_draft_config_file=None, forward_hooks=None, enable_quant_communications=False, msprobe_dump_config=None)
[2026-05-13 02:13:59] Hybrid swa model: self.hf_config.architectures=['DeepseekV4ForCausalLM']
[transformers] You are using a model of type `deepseek_v4` to instantiate a model of type ``. This may be expected if you are loading a checkpoint that shares a subset of the architecture (e.g., loading a `sam2_video` checkpoint into `Sam2Model`), but is otherwise not supported and can yield errors. Please verify that the checkpoint is compatible with the model you are instantiating.
[transformers] PreTrainedConfig got `key=rope_scaling` in kwargs but hasn't set it as attribute. For RoPE standardization you need to set `self.rope_parameters` in model's config.
[2026-05-13 02:14:00] Tokenizer loaded as generic TokenizersBackend for /eph/nvme/models/DeepSeek-V4-Flash-FP8, retrying with use_fast=False
[transformers] You are using a model of type `deepseek_v4` to instantiate a model of type ``. This may be expected if you are loading a checkpoint that shares a subset of the architecture (e.g., loading a `sam2_video` checkpoint into `Sam2Model`), but is otherwise not supported and can yield errors. Please verify that the checkpoint is compatible with the model you are instantiating.
[transformers] PreTrainedConfig got `key=rope_scaling` in kwargs but hasn't set it as attribute. For RoPE standardization you need to set `self.rope_parameters` in model's config.
[2026-05-13 02:14:00] Loading tokenizer for /eph/nvme/models/DeepSeek-V4-Flash-FP8 directly as PreTrainedTokenizerFast (bypassing AutoTokenizer)
[2026-05-13 02:14:01] Tokenizer for /eph/nvme/models/DeepSeek-V4-Flash-FP8 is still TokenizersBackend after retries with --trust-remote-code. Model-specific tokenizer attributes may be missing.
[2026-05-13 02:14:01] No HuggingFace chat template found
[2026-05-13 02:14:01] No chat template found, defaulting to 'string' content format
[aiter] import [module_aiter_core] under /sgl-workspace/aiter/aiter/jit/module_aiter_core.so
[aiter] import [module_aiter_core] under /sgl-workspace/aiter/aiter/jit/module_aiter_core.so
[aiter] merge tuned file under model_configs/ and configs/ /sgl-workspace/aiter/aiter/configs/bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/dsv3_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/dsv4_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/glm5_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/gptoss_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/kimik2_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/llama405B_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/llama70B_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/qwen32B_bf16_tuned_gemm.csv
[aiter] merge tuned file under model_configs/ and configs/ /sgl-workspace/aiter/aiter/configs/bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/dsv3_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/dsv4_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/glm5_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/gptoss_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/kimik2_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/llama405B_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/llama70B_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/qwen32B_bf16_tuned_gemm.csv
[transformers] You are using a model of type `deepseek_v4` to instantiate a model of type ``. This may be expected if you are loading a checkpoint that shares a subset of the architecture (e.g., loading a `sam2_video` checkpoint into `Sam2Model`), but is otherwise not supported and can yield errors. Please verify that the checkpoint is compatible with the model you are instantiating.
[transformers] PreTrainedConfig got `key=rope_scaling` in kwargs but hasn't set it as attribute. For RoPE standardization you need to set `self.rope_parameters` in model's config.
[2026-05-13 02:14:07] Tokenizer loaded as generic TokenizersBackend for /eph/nvme/models/DeepSeek-V4-Flash-FP8, retrying with use_fast=False
[transformers] You are using a model of type `deepseek_v4` to instantiate a model of type ``. This may be expected if you are loading a checkpoint that shares a subset of the architecture (e.g., loading a `sam2_video` checkpoint into `Sam2Model`), but is otherwise not supported and can yield errors. Please verify that the checkpoint is compatible with the model you are instantiating.
[transformers] PreTrainedConfig got `key=rope_scaling` in kwargs but hasn't set it as attribute. For RoPE standardization you need to set `self.rope_parameters` in model's config.
[2026-05-13 02:14:08] Loading tokenizer for /eph/nvme/models/DeepSeek-V4-Flash-FP8 directly as PreTrainedTokenizerFast (bypassing AutoTokenizer)
[2026-05-13 02:14:09] Tokenizer for /eph/nvme/models/DeepSeek-V4-Flash-FP8 is still TokenizersBackend after retries with --trust-remote-code. Model-specific tokenizer attributes may be missing.
[aiter] import [module_aiter_core] under /sgl-workspace/aiter/aiter/jit/module_aiter_core.so
[aiter] import [module_aiter_core] under /sgl-workspace/aiter/aiter/jit/module_aiter_core.so
[aiter] import [module_aiter_core] under /sgl-workspace/aiter/aiter/jit/module_aiter_core.so
[aiter] import [module_aiter_core] under /sgl-workspace/aiter/aiter/jit/module_aiter_core.so
[aiter] merge tuned file under model_configs/ and configs/ /sgl-workspace/aiter/aiter/configs/bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/dsv3_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/dsv4_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/glm5_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/gptoss_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/kimik2_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/llama405B_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/llama70B_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/qwen32B_bf16_tuned_gemm.csv
[aiter] merge tuned file under model_configs/ and configs/ /sgl-workspace/aiter/aiter/configs/bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/dsv3_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/dsv4_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/glm5_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/gptoss_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/kimik2_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/llama405B_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/llama70B_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/qwen32B_bf16_tuned_gemm.csv
[aiter] merge tuned file under model_configs/ and configs/ /sgl-workspace/aiter/aiter/configs/bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/dsv3_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/dsv4_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/glm5_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/gptoss_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/kimik2_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/llama405B_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/llama70B_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/qwen32B_bf16_tuned_gemm.csv
[aiter] merge tuned file under model_configs/ and configs/ /sgl-workspace/aiter/aiter/configs/bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/dsv3_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/dsv4_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/glm5_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/gptoss_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/kimik2_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/llama405B_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/llama70B_bf16_tuned_gemm.csv:/sgl-workspace/aiter/aiter/configs/model_configs/qwen32B_bf16_tuned_gemm.csv
[aiter] [pid=561 pname=Process-1:1] waiting for baton release at /tmp/aiter_configs/bf16_tuned_gemm.csv.lock
[aiter] [pid=562 pname=Process-1:2] waiting for baton release at /tmp/aiter_configs/bf16_tuned_gemm.csv.lock
[2026-05-13 02:14:14 DP2 TP2] Process 563 gpu_id 2 is running on CPUs: [48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71]
[2026-05-13 02:14:14 DP2 TP2] Hybrid swa model: self.hf_config.architectures=['DeepseekV4ForCausalLM']
[transformers] You are using a model of type `deepseek_v4` to instantiate a model of type ``. This may be expected if you are loading a checkpoint that shares a subset of the architecture (e.g., loading a `sam2_video` checkpoint into `Sam2Model`), but is otherwise not supported and can yield errors. Please verify that the checkpoint is compatible with the model you are instantiating.
[transformers] PreTrainedConfig got `key=rope_scaling` in kwargs but hasn't set it as attribute. For RoPE standardization you need to set `self.rope_parameters` in model's config.
[2026-05-13 02:14:14 DP3 TP3] Process 564 gpu_id 3 is running on CPUs: [72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95]
[2026-05-13 02:14:14 DP3 TP3] Hybrid swa model: self.hf_config.architectures=['DeepseekV4ForCausalLM']
[transformers] You are using a model of type `deepseek_v4` to instantiate a model of type ``. This may be expected if you are loading a checkpoint that shares a subset of the architecture (e.g., loading a `sam2_video` checkpoint into `Sam2Model`), but is otherwise not supported and can yield errors. Please verify that the checkpoint is compatible with the model you are instantiating.
[transformers] PreTrainedConfig got `key=rope_scaling` in kwargs but hasn't set it as attribute. For RoPE standardization you need to set `self.rope_parameters` in model's config.
[2026-05-13 02:14:14 DP0 TP0] Process 561 gpu_id 0 is running on CPUs: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
[2026-05-13 02:14:14 DP0 TP0] Hybrid swa model: self.hf_config.architectures=['DeepseekV4ForCausalLM']
[transformers] You are using a model of type `deepseek_v4` to instantiate a model of type ``. This may be expected if you are loading a checkpoint that shares a subset of the architecture (e.g., loading a `sam2_video` checkpoint into `Sam2Model`), but is otherwise not supported and can yield errors. Please verify that the checkpoint is compatible with the model you are instantiating.
[transformers] PreTrainedConfig got `key=rope_scaling` in kwargs but hasn't set it as attribute. For RoPE standardization you need to set `self.rope_parameters` in model's config.
[2026-05-13 02:14:14 DP2 TP2] Tokenizer loaded as generic TokenizersBackend for /eph/nvme/models/DeepSeek-V4-Flash-FP8, retrying with use_fast=False
[transformers] You are using a model of type `deepseek_v4` to instantiate a model of type ``. This may be expected if you are loading a checkpoint that shares a subset of the architecture (e.g., loading a `sam2_video` checkpoint into `Sam2Model`), but is otherwise not supported and can yield errors. Please verify that the checkpoint is compatible with the model you are instantiating.
[transformers] PreTrainedConfig got `key=rope_scaling` in kwargs but hasn't set it as attribute. For RoPE standardization you need to set `self.rope_parameters` in model's config.
[2026-05-13 02:14:15 DP1 TP1] Process 562 gpu_id 1 is running on CPUs: [24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47]
[2026-05-13 02:14:15 DP1 TP1] Hybrid swa model: self.hf_config.architectures=['DeepseekV4ForCausalLM']
[transformers] You are using a model of type `deepseek_v4` to instantiate a model of type ``. This may be expected if you are loading a checkpoint that shares a subset of the architecture (e.g., loading a `sam2_video` checkpoint into `Sam2Model`), but is otherwise not supported and can yield errors. Please verify that the checkpoint is compatible with the model you are instantiating.
[transformers] PreTrainedConfig got `key=rope_scaling` in kwargs but hasn't set it as attribute. For RoPE standardization you need to set `self.rope_parameters` in model's config.
[2026-05-13 02:14:15 DP3 TP3] Tokenizer loaded as generic TokenizersBackend for /eph/nvme/models/DeepSeek-V4-Flash-FP8, retrying with use_fast=False
[transformers] You are using a model of type `deepseek_v4` to instantiate a model of type ``. This may be expected if you are loading a checkpoint that shares a subset of the architecture (e.g., loading a `sam2_video` checkpoint into `Sam2Model`), but is otherwise not supported and can yield errors. Please verify that the checkpoint is compatible with the model you are instantiating.
[transformers] PreTrainedConfig got `key=rope_scaling` in kwargs but hasn't set it as attribute. For RoPE standardization you need to set `self.rope_parameters` in model's config.
[2026-05-13 02:14:15 DP0 TP0] Tokenizer loaded as generic TokenizersBackend for /eph/nvme/models/DeepSeek-V4-Flash-FP8, retrying with use_fast=False
[transformers] You are using a model of type `deepseek_v4` to instantiate a model of type ``. This may be expected if you are loading a checkpoint that shares a subset of the architecture (e.g., loading a `sam2_video` checkpoint into `Sam2Model`), but is otherwise not supported and can yield errors. Please verify that the checkpoint is compatible with the model you are instantiating.
[transformers] PreTrainedConfig got `key=rope_scaling` in kwargs but hasn't set it as attribute. For RoPE standardization you need to set `self.rope_parameters` in model's config.
[2026-05-13 02:14:15 DP2 TP2] Loading tokenizer for /eph/nvme/models/DeepSeek-V4-Flash-FP8 directly as PreTrainedTokenizerFast (bypassing AutoTokenizer)
[2026-05-13 02:14:15 DP1 TP1] Tokenizer loaded as generic TokenizersBackend for /eph/nvme/models/DeepSeek-V4-Flash-FP8, retrying with use_fast=False
[transformers] You are using a model of type `deepseek_v4` to instantiate a model of type ``. This may be expected if you are loading a checkpoint that shares a subset of the architecture (e.g., loading a `sam2_video` checkpoint into `Sam2Model`), but is otherwise not supported and can yield errors. Please verify that the checkpoint is compatible with the model you are instantiating.
[transformers] PreTrainedConfig got `key=rope_scaling` in kwargs but hasn't set it as attribute. For RoPE standardization you need to set `self.rope_parameters` in model's config.
[2026-05-13 02:14:16 DP3 TP3] Loading tokenizer for /eph/nvme/models/DeepSeek-V4-Flash-FP8 directly as PreTrainedTokenizerFast (bypassing AutoTokenizer)
[2026-05-13 02:14:16 DP0 TP0] Loading tokenizer for /eph/nvme/models/DeepSeek-V4-Flash-FP8 directly as PreTrainedTokenizerFast (bypassing AutoTokenizer)
[2026-05-13 02:14:16 DP2 TP2] Tokenizer for /eph/nvme/models/DeepSeek-V4-Flash-FP8 is still TokenizersBackend after retries with --trust-remote-code. Model-specific tokenizer attributes may be missing.
[2026-05-13 02:14:16 DP1 TP1] Loading tokenizer for /eph/nvme/models/DeepSeek-V4-Flash-FP8 directly as PreTrainedTokenizerFast (bypassing AutoTokenizer)
[2026-05-13 02:14:16 DP2 TP2] Hybrid swa model: self.hf_config.architectures=['DeepseekV4ForCausalLM']
[2026-05-13 02:14:16 DP2 TP2] Init torch distributed begin.
[W513 02:14:16.134534856 socket.cpp:767] [c10d] The client socket cannot be initialized to connect to [localhost]:41319 (errno: 97 - Address family not supported by protocol).
[2026-05-13 02:14:16 DP3 TP3] Tokenizer for /eph/nvme/models/DeepSeek-V4-Flash-FP8 is still TokenizersBackend after retries with --trust-remote-code. Model-specific tokenizer attributes may be missing.
[2026-05-13 02:14:17 DP3 TP3] Hybrid swa model: self.hf_config.architectures=['DeepseekV4ForCausalLM']
[2026-05-13 02:14:17 DP3 TP3] Init torch distributed begin.
[W513 02:14:17.426616519 socket.cpp:767] [c10d] The client socket cannot be initialized to connect to [localhost]:41319 (errno: 97 - Address family not supported by protocol).
[2026-05-13 02:14:17 DP0 TP0] Tokenizer for /eph/nvme/models/DeepSeek-V4-Flash-FP8 is still TokenizersBackend after retries with --trust-remote-code. Model-specific tokenizer attributes may be missing.
[2026-05-13 02:14:17 DP1 TP1] Tokenizer for /eph/nvme/models/DeepSeek-V4-Flash-FP8 is still TokenizersBackend after retries with --trust-remote-code. Model-specific tokenizer attributes may be missing.
[2026-05-13 02:14:17 DP0 TP0] Hybrid swa model: self.hf_config.architectures=['DeepseekV4ForCausalLM']
[2026-05-13 02:14:17 DP0 TP0] Init torch distributed begin.
[2026-05-13 02:14:17 DP1 TP1] Hybrid swa model: self.hf_config.architectures=['DeepseekV4ForCausalLM']
[2026-05-13 02:14:17 DP1 TP1] Init torch distributed begin.
[W513 02:14:17.863172540 socket.cpp:767] [c10d] The client socket cannot be initialized to connect to [localhost]:41319 (errno: 97 - Address family not supported by protocol).
[W513 02:14:17.867118366 socket.cpp:767] [c10d] The client socket cannot be initialized to connect to [localhost]:41319 (errno: 97 - Address family not supported by protocol).
[Gloo] Rank 0 is connected to 3 peer ranks. Expected number of connected peer ranks is : 3
[Gloo] Rank 2 is connected to 3 peer ranks. Expected number of connected peer ranks is : 3
[Gloo] Rank 1 is connected to 3 peer ranks. Expected number of connected peer ranks is : 3
[Gloo] Rank 3 is connected to 3 peer ranks. Expected number of connected peer ranks is : 3
[2026-05-13 02:14:17 DP3 TP3] [AR] All-reduce call path: NCCL (custom AR disabled)
[2026-05-13 02:14:17 DP2 TP2] [AR] All-reduce call path: NCCL (custom AR disabled)
[2026-05-13 02:14:17 DP1 TP1] [AR] All-reduce call path: NCCL (custom AR disabled)
[2026-05-13 02:14:17 DP0 TP0] [AR] All-reduce call path: NCCL (custom AR disabled)
[Gloo] Rank 1 is connected to 3 peer ranks. Expected number of connected peer ranks is : 3
[Gloo] Rank 3 is connected to 3 peer ranks. Expected number of connected peer ranks is : 3
[Gloo] Rank 0 is connected to 3 peer ranks. Expected number of connected peer ranks is : 3
[Gloo] Rank 2 is connected to 3 peer ranks. Expected number of connected peer ranks is : 3
[2026-05-13 02:14:17 DP0 TP0] sglang is using nccl==2.27.7
[aiter] import [module_custom_all_reduce] under /sgl-workspace/aiter/aiter/jit/module_custom_all_reduce.so
[aiter] import [module_custom_all_reduce] under /sgl-workspace/aiter/aiter/jit/module_custom_all_reduce.so
[aiter] import [module_custom_all_reduce] under /sgl-workspace/aiter/aiter/jit/module_custom_all_reduce.so
[aiter] import [module_custom_all_reduce] under /sgl-workspace/aiter/aiter/jit/module_custom_all_reduce.so
[2026-05-13 02:14:33 DP3 TP3] [AR] Using AiterCustomAllreduce (AMD default)
[2026-05-13 02:14:33 DP1 TP1] [AR] Using AiterCustomAllreduce (AMD default)
[2026-05-13 02:14:33 DP2 TP2] [AR] Using AiterCustomAllreduce (AMD default)
[2026-05-13 02:14:33 DP0 TP0] [AR] Using AiterCustomAllreduce (AMD default)
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[2026-05-13 02:14:33 DP0 TP0] Init torch distributed ends. elapsed=16.23 s, mem usage=8.29 GB
[2026-05-13 02:14:33 DP3 TP3] Init torch distributed ends. elapsed=16.52 s, mem usage=8.24 GB
[2026-05-13 02:14:33 DP2 TP2] Init torch distributed ends. elapsed=16.82 s, mem usage=8.29 GB
[2026-05-13 02:14:33 DP1 TP1] Init torch distributed ends. elapsed=16.08 s, mem usage=8.31 GB
[2026-05-13 02:14:33 DP3 TP3] Ignore import error when loading sglang.srt.models.afmoe: cannot import name 'fused_moe' from 'sglang.srt.layers.moe.fused_moe_triton' (/sgl-workspace/sglang/python/sglang/srt/layers/moe/fused_moe_triton/__init__.py)
[2026-05-13 02:14:33 DP0 TP0] Ignore import error when loading sglang.srt.models.afmoe: cannot import name 'fused_moe' from 'sglang.srt.layers.moe.fused_moe_triton' (/sgl-workspace/sglang/python/sglang/srt/layers/moe/fused_moe_triton/__init__.py)
[2026-05-13 02:14:33 DP1 TP1] Ignore import error when loading sglang.srt.models.afmoe: cannot import name 'fused_moe' from 'sglang.srt.layers.moe.fused_moe_triton' (/sgl-workspace/sglang/python/sglang/srt/layers/moe/fused_moe_triton/__init__.py)
[2026-05-13 02:14:33 DP2 TP2] Ignore import error when loading sglang.srt.models.afmoe: cannot import name 'fused_moe' from 'sglang.srt.layers.moe.fused_moe_triton' (/sgl-workspace/sglang/python/sglang/srt/layers/moe/fused_moe_triton/__init__.py)
[2026-05-13 02:14:33 DP3 TP3] Loading tilelang libs from dev root: /opt/tilelang/build
[2026-05-13 02:14:33 DP1 TP1] Loading tilelang libs from dev root: /opt/tilelang/build
[2026-05-13 02:14:33 DP2 TP2] Loading tilelang libs from dev root: /opt/tilelang/build
[2026-05-13 02:14:33 DP0 TP0] Loading tilelang libs from dev root: /opt/tilelang/build
/opt/venv/lib/python3.10/site-packages/apex/transformer/functional/fused_rope.py:49: UserWarning: Aiter backend is selected for fused RoPE. This has lower precision. To disable aiter, export USE_ROCM_AITER_ROPE_BACKEND=0
  warnings.warn("Aiter backend is selected for fused RoPE. This has lower precision. To disable aiter, export USE_ROCM_AITER_ROPE_BACKEND=0", UserWarning)
/opt/venv/lib/python3.10/site-packages/apex/transformer/functional/fused_rope.py:49: UserWarning: Aiter backend is selected for fused RoPE. This has lower precision. To disable aiter, export USE_ROCM_AITER_ROPE_BACKEND=0
  warnings.warn("Aiter backend is selected for fused RoPE. This has lower precision. To disable aiter, export USE_ROCM_AITER_ROPE_BACKEND=0", UserWarning)
/opt/venv/lib/python3.10/site-packages/apex/transformer/functional/fused_rope.py:49: UserWarning: Aiter backend is selected for fused RoPE. This has lower precision. To disable aiter, export USE_ROCM_AITER_ROPE_BACKEND=0
  warnings.warn("Aiter backend is selected for fused RoPE. This has lower precision. To disable aiter, export USE_ROCM_AITER_ROPE_BACKEND=0", UserWarning)
/opt/venv/lib/python3.10/site-packages/apex/transformer/functional/fused_rope.py:49: UserWarning: Aiter backend is selected for fused RoPE. This has lower precision. To disable aiter, export USE_ROCM_AITER_ROPE_BACKEND=0
  warnings.warn("Aiter backend is selected for fused RoPE. This has lower precision. To disable aiter, export USE_ROCM_AITER_ROPE_BACKEND=0", UserWarning)
[2026-05-13 02:14:34 DP3 TP3] aiter fused_qk_norm_mrope_3d kernel available
[2026-05-13 02:14:34 DP1 TP1] aiter fused_qk_norm_mrope_3d kernel available
[2026-05-13 02:14:34 DP2 TP2] aiter fused_qk_norm_mrope_3d kernel available
[2026-05-13 02:14:34 DP0 TP0] aiter fused_qk_norm_mrope_3d kernel available
[2026-05-13 02:14:35 DP0 TP0] Load weight begin. avail mem=182.63 GB
[2026-05-13 02:14:35 DP0 TP0] Detected fp8 checkpoint.
[2026-05-13 02:14:35 DP3 TP3] Load weight begin. avail mem=182.67 GB
[2026-05-13 02:14:35 DP2 TP2] Load weight begin. avail mem=182.63 GB
[2026-05-13 02:14:35 DP1 TP1] Load weight begin. avail mem=182.61 GB
Multi-thread loading shards: 100% Completed | 46/46 [00:16<00:00,  2.85it/s]
[2026-05-13 02:15:17 DP2 TP2] Using FP8 KV cache but no scaling factors provided. Defaulting to scaling factors of 1.0. This may lead to less accurate results!
[2026-05-13 02:15:17 DP2 TP2] Load weight end. elapsed=41.51 s, type=DeepseekV4ForCausalLM, quant=fp8, fmt=e4m3, avail mem=109.20 GB, mem usage=73.43 GB.
[2026-05-13 02:15:17 DP3 TP3] Using FP8 KV cache but no scaling factors provided. Defaulting to scaling factors of 1.0. This may lead to less accurate results!
[2026-05-13 02:15:17 DP3 TP3] Load weight end. elapsed=41.79 s, type=DeepseekV4ForCausalLM, quant=fp8, fmt=e4m3, avail mem=109.24 GB, mem usage=73.43 GB.
[2026-05-13 02:15:17 DP1 TP1] Using FP8 KV cache but no scaling factors provided. Defaulting to scaling factors of 1.0. This may lead to less accurate results!
[2026-05-13 02:15:17 DP1 TP1] Load weight end. elapsed=42.20 s, type=DeepseekV4ForCausalLM, quant=fp8, fmt=e4m3, avail mem=109.18 GB, mem usage=73.43 GB.
[2026-05-13 02:15:18 DP0 TP0] Using FP8 KV cache but no scaling factors provided. Defaulting to scaling factors of 1.0. This may lead to less accurate results!
[2026-05-13 02:15:18 DP0 TP0] Load weight end. elapsed=42.37 s, type=DeepseekV4ForCausalLM, quant=fp8, fmt=e4m3, avail mem=109.20 GB, mem usage=73.43 GB.
[2026-05-13 02:15:18 DP0 TP0] Using KV cache dtype: torch.float8_e4m3fnuz
[2026-05-13 02:15:18 DP0 TP0] DSv4 memory calculation: bytes_per_full_token=176983.05, available_bytes=87.26 GB, full_token=529408
[2026-05-13 02:15:18 DP3 TP3] DSv4 memory calculation: bytes_per_full_token=176983.05, available_bytes=87.26 GB, full_token=529408
[2026-05-13 02:15:18 DP1 TP1] DSv4 memory calculation: bytes_per_full_token=176983.05, available_bytes=87.26 GB, full_token=529408
[2026-05-13 02:15:18 DP2 TP2] DSv4 memory calculation: bytes_per_full_token=176983.05, available_bytes=87.26 GB, full_token=529408
[2026-05-13 02:15:18 DP0 TP0] Initialize DeepSeekV4TokenToKVPool with max_num_reqs=256 swa_size=423424 c4_size=132352 c128_size=4136 c4_state_pool_size=52928 c128_state_pool_size=846848
[2026-05-13 02:15:18 DP3 TP3] Initialize DeepSeekV4TokenToKVPool with max_num_reqs=256 swa_size=423424 c4_size=132352 c128_size=4136 c4_state_pool_size=52928 c128_state_pool_size=846848
[2026-05-13 02:15:18 DP2 TP2] Initialize DeepSeekV4TokenToKVPool with max_num_reqs=256 swa_size=423424 c4_size=132352 c128_size=4136 c4_state_pool_size=52928 c128_state_pool_size=846848
[2026-05-13 02:15:18 DP1 TP1] Initialize DeepSeekV4TokenToKVPool with max_num_reqs=256 swa_size=423424 c4_size=132352 c128_size=4136 c4_state_pool_size=52928 c128_state_pool_size=846848
[2026-05-13 02:15:18 DP3 TP3] Scheduler hit an exception: Traceback (most recent call last):
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 3958, in run_scheduler_process
    scheduler = Scheduler(
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 433, in __init__
    self.init_model_worker()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 704, in init_model_worker
    self.init_tp_model_worker()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 659, in init_tp_model_worker
    self.tp_worker = TpModelWorker(**worker_kwargs)
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 260, in __init__
    self._init_model_runner()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 345, in _init_model_runner
    self._model_runner = ModelRunner(
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 526, in __init__
    self.initialize(pre_model_load_memory)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 736, in initialize
    self.init_memory_pool(pre_model_load_memory)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py", line 824, in init_memory_pool
    self._apply_memory_pool_config(self.memory_pool_config)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py", line 785, in _apply_memory_pool_config
    self._init_pools()
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py", line 308, in _init_pools
    self.token_to_kv_pool = DeepSeekV4TokenToKVPool(
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 472, in __init__
    self.swa_kv_pool = DeepSeekV4SingleKVPool(
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 83, in __init__
    self._create_buffers()
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 108, in _create_buffers
    self.kv_buffer = [
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 109, in <listcomp>
    self.create_buffer(
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 144, in create_buffer
    assert self.store_dtype == torch.uint8
AssertionError

[2026-05-13 02:15:18 DP0 TP0] Scheduler hit an exception: Traceback (most recent call last):
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 3958, in run_scheduler_process
    scheduler = Scheduler(
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 433, in __init__
    self.init_model_worker()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 704, in init_model_worker
    self.init_tp_model_worker()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 659, in init_tp_model_worker
    self.tp_worker = TpModelWorker(**worker_kwargs)
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 260, in __init__
    self._init_model_runner()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 345, in _init_model_runner
    self._model_runner = ModelRunner(
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 526, in __init__
    self.initialize(pre_model_load_memory)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 736, in initialize
    self.init_memory_pool(pre_model_load_memory)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py", line 824, in init_memory_pool
    self._apply_memory_pool_config(self.memory_pool_config)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py", line 785, in _apply_memory_pool_config
    self._init_pools()
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py", line 308, in _init_pools
    self.token_to_kv_pool = DeepSeekV4TokenToKVPool(
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 472, in __init__
    self.swa_kv_pool = DeepSeekV4SingleKVPool(
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 83, in __init__
    self._create_buffers()
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 108, in _create_buffers
    self.kv_buffer = [
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 109, in <listcomp>
    self.create_buffer(
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 144, in create_buffer
    assert self.store_dtype == torch.uint8
AssertionError

[2026-05-13 02:15:18 DP1 TP1] Scheduler hit an exception: Traceback (most recent call last):
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 3958, in run_scheduler_process
    scheduler = Scheduler(
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 433, in __init__
    self.init_model_worker()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 704, in init_model_worker
    self.init_tp_model_worker()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 659, in init_tp_model_worker
    self.tp_worker = TpModelWorker(**worker_kwargs)
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 260, in __init__
    self._init_model_runner()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 345, in _init_model_runner
    self._model_runner = ModelRunner(
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 526, in __init__
    self.initialize(pre_model_load_memory)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 736, in initialize
    self.init_memory_pool(pre_model_load_memory)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py", line 824, in init_memory_pool
    self._apply_memory_pool_config(self.memory_pool_config)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py", line 785, in _apply_memory_pool_config
    self._init_pools()
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py", line 308, in _init_pools
    self.token_to_kv_pool = DeepSeekV4TokenToKVPool(
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 472, in __init__
    self.swa_kv_pool = DeepSeekV4SingleKVPool(
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 83, in __init__
    self._create_buffers()
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 108, in _create_buffers
    self.kv_buffer = [
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 109, in <listcomp>
    self.create_buffer(
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 144, in create_buffer
    assert self.store_dtype == torch.uint8
AssertionError

[2026-05-13 02:15:18 DP2 TP2] Scheduler hit an exception: Traceback (most recent call last):
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 3958, in run_scheduler_process
    scheduler = Scheduler(
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 433, in __init__
    self.init_model_worker()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 704, in init_model_worker
    self.init_tp_model_worker()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 659, in init_tp_model_worker
    self.tp_worker = TpModelWorker(**worker_kwargs)
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 260, in __init__
    self._init_model_runner()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 345, in _init_model_runner
    self._model_runner = ModelRunner(
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 526, in __init__
    self.initialize(pre_model_load_memory)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 736, in initialize
    self.init_memory_pool(pre_model_load_memory)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py", line 824, in init_memory_pool
    self._apply_memory_pool_config(self.memory_pool_config)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py", line 785, in _apply_memory_pool_config
    self._init_pools()
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py", line 308, in _init_pools
    self.token_to_kv_pool = DeepSeekV4TokenToKVPool(
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 472, in __init__
    self.swa_kv_pool = DeepSeekV4SingleKVPool(
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 83, in __init__
    self._create_buffers()
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 108, in _create_buffers
    self.kv_buffer = [
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 109, in <listcomp>
    self.create_buffer(
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/deepseekv4_memory_pool.py", line 144, in create_buffer
    assert self.store_dtype == torch.uint8
AssertionError

[rank0]:[W513 02:15:19.747860733 ProcessGroupNCCL.cpp:1524] Warning: WARNING: destroy_process_group() was not called before program exit, which can leak resources. For more info, please see https://pytorch.org/docs/stable/distributed.html#shutdown (function operator())
Traceback (most recent call last):
  File "/sgl-workspace/sglang/python/sglang/srt/entrypoints/engine.py", line 1275, in _wait_for_scheduler_ready
    data = scheduler_pipe_readers[i].recv()
  File "/usr/lib/python3.10/multiprocessing/connection.py", line 250, in recv
    buf = self._recv_bytes()
  File "/usr/lib/python3.10/multiprocessing/connection.py", line 414, in _recv_bytes
    buf = self._recv(4)
  File "/usr/lib/python3.10/multiprocessing/connection.py", line 383, in _recv
    raise EOFError
EOFError

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/usr/lib/python3.10/runpy.py", line 196, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/usr/lib/python3.10/runpy.py", line 86, in _run_code
    exec(code, run_globals)
  File "/sgl-workspace/sglang/python/sglang/launch_server.py", line 69, in <module>
    run_server(server_args)
  File "/sgl-workspace/sglang/python/sglang/launch_server.py", line 50, in run_server
    launch_server(server_args)
  File "/sgl-workspace/sglang/python/sglang/srt/entrypoints/http_server.py", line 2346, in launch_server
    ) = Engine._launch_subprocesses(
  File "/sgl-workspace/sglang/python/sglang/srt/entrypoints/engine.py", line 796, in _launch_subprocesses
    scheduler_init_result.wait_for_ready()
  File "/sgl-workspace/sglang/python/sglang/srt/entrypoints/engine.py", line 647, in wait_for_ready
    infos = _wait_for_scheduler_ready(scheduler_pipe_readers, scheduler_procs)
  File "/sgl-workspace/sglang/python/sglang/srt/entrypoints/engine.py", line 1277, in _wait_for_scheduler_ready
    raise _scheduler_died_error(i, scheduler_procs[i])
RuntimeError: Rank 0 scheduler died during initialization (exit code: -3). If exit code is -9 (SIGKILL), a common cause is the OS OOM killer. Run `dmesg -T | grep -i oom` to check.
```

### Environment

```
python3 -m sglang.check_env
WARNING: AMD GPU device(s) is/are in a low-power state. Check power control/runtime_status

Python: 3.10.12 (main, Jan  8 2026, 06:52:19) [GCC 11.4.0]
ROCM available: True
GPU 0,1,2,3: AMD Instinct MI300X VF
GPU 0,1,2,3 Compute Capability: 9.4
ROCM_HOME: /opt/rocm-7.2.0
HIPCC: HIP version: 7.2.26015-fc0010cf6a
ROCM Driver Version: 6.8.5
PyTorch: 2.9.1+rocm7.2.0.git7e1940d4
sglang: 0.5.11.dev20260512+g339e36e
sglang-kernel: 0.4.2.post1
flashinfer_python: Module Not Found
flashinfer_cubin: Module Not Found
flashinfer_jit_cache: Module Not Found
triton: 3.6.0+git42270451
transformers: 5.6.0
torchao: 0.9.0
numpy: 2.2.6
aiohttp: 3.13.5
fastapi: 0.136.1
huggingface_hub: 1.14.0
interegular: 0.3.3
modelscope: 1.36.3
orjson: 3.11.9
outlines: 0.1.11
packaging: 25.0
psutil: 7.2.2
pydantic: 2.13.4
python-multipart: 0.0.28
pyzmq: 27.1.0
uvicorn: 0.46.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.2.0
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.101.0
litellm: Module Not Found
torchcodec: Module Not Found
AMD Topology:


============================ ROCm System Management Interface ============================
=============================== Link Type between two GPUs ===============================
       GPU0         GPU1         GPU2         GPU3         GPU4         GPU5         GPU6         GPU7
GPU0   0            XGMI         XGMI         XGMI         XGMI         XGMI         XGMI         XGMI
GPU1   XGMI         0            XGMI         XGMI         XGMI         XGMI         XGMI         XGMI
GPU2   XGMI         XGMI         0            XGMI         XGMI         XGMI         XGMI         XGMI
GPU3   XGMI         XGMI         XGMI         0            XGMI         XGMI         XGMI         XGMI
GPU4   XGMI         XGMI         XGMI         XGMI         0            XGMI         XGMI         XGMI
GPU5   XGMI         XGMI         XGMI         XGMI         XGMI         0            XGMI         XGMI
GPU6   XGMI         XGMI         XGMI         XGMI         XGMI         XGMI         0            XGMI
GPU7   XGMI         XGMI         XGMI         XGMI         XGMI         XGMI         XGMI         0
================================== End of ROCm SMI Log ===================================

Hypervisor vendor:: Microsoft
ulimit soft: 65535
```
