---
source_id: sglang-github-closed-issues-prs
title: bugfix for npu Grok2 model --detokenizer without all special ids
canonical_url: https://github.com/sgl-project/sglang/pull/29853
captured_at: '2026-07-03T02:13:21.698957+00:00'
content_hash: 5425def01772eb984f6db792cc05c0c853ff94431bed8bbe64ec9635eb85bf37
---
# bugfix for npu Grok2 model --detokenizer without all special ids

URL: https://github.com/sgl-project/sglang/pull/29853
State: closed
Labels: run-ci
Closed at: 2026-07-02T14:12:48Z
Merged at: 2026-07-02T14:12:48Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation
bugfix for error #25309 that 'TiktokenTokenizer' object has no attribute 'all_special_ids'
[2026-05-29 12:21:03] DetokenizerManager hit an exception: Traceback (most recent call last):
  File "/sgl-workspace/sglang/python/sglang/srt/managers/detokenizer_manager.py", line 440, in run_detokenizer_process
    manager.event_loop()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/detokenizer_manager.py", line 150, in event_loop
    output = self._request_dispatcher(recv_obj)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/utils.py", line 649, in __call__
    return fn(obj)
           ^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/managers/detokenizer_manager.py", line 358, in handle_batch_token_id_out
    self._decode_batch_token_id_output(recv_obj)
  File "/sgl-workspace/sglang/python/sglang/srt/managers/detokenizer_manager.py", line 261, in _decode_batch_token_id_output
    surr_texts = self._grouped_batch_decode(
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/managers/detokenizer_manager.py", line 195, in _grouped_batch_decode
    return [
           ^
  File "/sgl-workspace/sglang/python/sglang/srt/managers/detokenizer_manager.py", line 196, in <listcomp>
    decode_without_hf_kwargs(self.tokenizer, ids, skip)
  File "/sgl-workspace/sglang/python/sglang/srt/utils/patch_tokenizer.py", line 36, in decode_without_hf_kwargs
    special_ids = set(tokenizer.all_special_ids)
                      ^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'TiktokenTokenizer' object has no attribute 'all_special_ids'
<!-- Describe the purpose and goals of this pull request. -->

## Modifications

as follows
<!-- Detail the changes made in this pull request. -->

## Accuracy Tests

command=sglang serve --model-path /data/weights/grok-2 --trust-remote-code --mem-fraction-static 0.8 --attention-backend ascend --disable-radix-cache --disable-cuda-graph --tokenizer-path /data/weights/grok-2/tokenizer.tok.json --tp-size 16 --base-gpu-id 0 --port 0809 --device npu --host 127.0.0.1 --port 21000
CI_OFFLINE: Launching server HF_HUB_OFFLINE=0 model=/data/weights/grok-2
'--disable-cuda-graph' is deprecated and will be removed in a future release. Use '--cuda-graph-backend-{decode,prefill}=disabled' instead.
[2026-07-01 15:18:33] get env TORCHINDUCTOR_CACHE_DIR = /tmp/torchinductor_root
[2026-07-01 15:18:34] get env LD_LIBRARY_PATH = /usr/local/Ascend/nnal/atb/latest/atb/cxx_abi_1/lib:/usr/local/Ascend/nnal/atb/latest/atb/cxx_abi_1/examples:/usr/local/Ascend/nnal/atb/latest/atb/cxx_abi_1/tests/atbopstest:/usr/local/Ascend/cann-9.0.0/lib64:/usr/local/Ascend/cann-9.0.0/lib64/plugin/opskernel:/usr/local/Ascend/cann-9.0.0/lib64/plugin/nnengine:/usr/local/Ascend/cann-9.0.0/opp/built-in/op_impl/ai_core/tbe/op_tiling/lib/linux/aarch64:/usr/local/Ascend/driver/lib64:/usr/local/Ascend/driver/lib64/common:/usr/local/Ascend/driver/lib64/driver:/usr/local/Ascend/driver/lib64:/usr/local/Ascend/driver/lib64/common:/usr/local/Ascend/driver/lib64/driver:/usr/local/Ascend/nnal/atb/latest/atb/cxx_abi_1/lib:/usr/local/Ascend/nnal/atb/latest/atb/cxx_abi_1/examples:/usr/local/Ascend/nnal/atb/latest/atb/cxx_abi_1/tests/atbopstest:/usr/local/Ascend/ascend-toolkit/latest/tools/aml/lib64:/usr/local/Ascend/ascend-toolkit/latest/tools/aml/lib64/plugin:/usr/local/Ascend/ascend-toolkit/latest/lib64:/usr/local/Ascend/ascend-toolkit/latest/lib64/plugin/opskernel:/usr/local/Ascend/ascend-toolkit/latest/lib64/plugin/nnengine:/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe/op_tiling:/usr/local/python3.11.15/lib:
[2026-07-01 15:18:34] Failed to load generation config for /data/weights/grok-2: /data/weights/grok-2 does not appear to have a file named generation_config.json. Checkout 'https://huggingface.co//data/weights/grok-2/tree/main' for available files.. Proceeding without generation config.
[2026-07-01 15:18:35] get env HOSTNAME = os-node-created-8fmx9
[2026-07-01 15:18:36] server_args=ServerArgs(model_path='/data/weights/grok-2', tokenizer_path='/data/weights/grok-2/tokenizer.tok.json', tokenizer_mode='auto', tokenizer_backend='huggingface', tokenizer_worker_num=1, detokenizer_worker_num=1, skip_tokenizer_init=False, load_format='auto', model_loader_extra_config='{}', trust_remote_code=True, context_length=None, is_embedding=False, enable_multimodal=None, revision=None, model_impl='auto', model_config_parser='auto', json_model_override_args='{}', host='127.0.0.1', port=21000, fastapi_root_path='', grpc_mode=False, skip_server_warmup=False, warmups=None, enable_http2=False, ssl_keyfile=None, ssl_certfile=None, ssl_ca_certs=None, ssl_keyfile_password=None, enable_ssl_refresh=False, dtype='auto', quantization=None, quantization_param_path=None, kv_cache_dtype='auto', enable_fp32_lm_head=False, modelopt_quant=None, modelopt_checkpoint_restore_path=None, modelopt_checkpoint_save_path=None, modelopt_export_path=None, quantize_and_serve=False, rl_quant_profile=None, enable_tf32_matmul=False, mem_fraction_static=0.8, max_running_requests=None, max_queued_requests=None, max_total_tokens=None, chunked_prefill_size=8192, enable_dynamic_chunking=False, max_prefill_tokens=16384, prefill_max_requests=None, schedule_policy='fcfs', enable_priority_scheduling=False, disable_priority_preemption=False, default_priority_value=None, abort_on_priority_when_disabled=False, schedule_low_priority_values_first=False, priority_scheduling_preemption_threshold=10, schedule_conservativeness=1.0, page_size=128, swa_full_tokens_ratio=0.8, disable_hybrid_swa_memory=False, radix_eviction_policy='lru', prefill_only_disable_kv_cache=False, disable_radix_cache=True, enable_page_major_kv_layout=False, disable_chunked_prefix_cache=False, disable_overlap_schedule=False, num_continuous_decode_steps=1, scheduler_recv_interval=1, enable_mixed_chunk=False, device='npu', base_gpu_id=0, gpu_id_step=1, random_seed=582814479, watchdog_timeout=300, soft_watchdog_timeout=None, sleep_on_idle=False, use_ray=False, custom_sigquit_handler=None, numa_node=None, gc_threshold=None, nccl_port=None, dist_timeout=None, dist_init_addr=None, nnodes=1, node_rank=0, tp_size=16, dcp_size=1, pp_size=1, pp_max_micro_batch_size=None, pp_async_batch_depth=0, dp_size=1, load_balance_method='round_robin', attn_cp_size=1, moe_dp_size=1, enable_prefill_cp=False, cp_strategy=None, enable_dsa_prefill_context_parallel=False, dsa_prefill_cp_mode='round-robin-split', enable_prefill_context_parallel=False, prefill_cp_mode='in-seq-split', enable_dp_attention=False, enable_dp_attention_local_control_broadcast=False, enable_dp_lm_head=False, enable_attn_tp_input_scattered=False, disable_attn_tp_gather=False, enable_p2p_check=False, stream_interval=1, batch_notify_size=16, stream_response_default_include_usage=False, incremental_streaming_output=False, enable_streaming_session=False, enable_session_radix_cache=False, constrained_json_whitespace_pattern=None, constrained_json_disable_any_whitespace=False, log_level='info', log_level_http=None, log_requests=False, log_requests_level=2, log_requests_format='text', log_requests_target=None, uvicorn_access_log_exclude_prefixes=[], crash_dump_folder=None, show_time_cost=False, enable_metrics=False, grpc_http_sidecar_port=None, enable_mfu_metrics=False, enable_metrics_for_all_schedulers=False, load_snapshot_publish_interval=15, tokenizer_metrics_custom_labels_header='x-custom-labels', tokenizer_metrics_allowed_custom_labels=None, extra_metric_labels=None, bucket_time_to_first_token=None, bucket_inter_token_latency=None, bucket_e2e_request_latency=None, prompt_tokens_buckets=None, generation_tokens_buckets=None, gc_warning_threshold_secs=0.0, decode_log_interval=40, enable_request_time_stats_logging=False, kv_events_config=None, enable_forward_pass_metrics=False, forward_pass_metrics_worker_id='', forward_pass_metrics_ipc_name=None, enable_trace=False, trace_modules='request', otlp_traces_endpoint='localhost:4317', export_metrics_to_file=False, export_metrics_to_file_dir=None, stat_loggers=None, api_key=None, admin_api_key=None, served_model_name='/data/weights/grok-2', weight_version='default', chat_template=None, hf_chat_template_name=None, completion_template=None, file_storage_path='sglang_storage', enable_cache_report=False, reasoning_parser=None, strip_thinking_cache=False, enable_strict_thinking=False, tool_call_parser=None, tool_server=None, sampling_defaults='model', asr_max_buffer_seconds=60, asr_max_concurrent_sessions=32, preferred_sampling_params=None, allow_auto_truncate=False, enable_prefill_delayer=False, prefill_delayer_max_delay_passes=30, prefill_delayer_token_usage_low_watermark=None, prefill_delayer_forward_passes_buckets=None, prefill_delayer_wait_seconds_buckets=None, prefill_delayer_queue_min_ratio=None, prefill_delayer_max_delay_ms=None, min_free_slots_delay=None, enable_lora=None, enable_lora_overlap_loading=None, max_lora_rank=None, lora_target_modules=None, lora_paths=None, max_loaded_loras=None, max_loras_per_batch=8, lora_eviction_policy='lru', lora_backend='csgmv', max_lora_chunk_size=16, experts_shared_outer_loras=None, lora_use_virtual_experts=False, lora_strict_loading=False, lora_drain_wait_threshold=0.0, attention_backend='ascend', decode_attention_backend='ascend', prefill_attention_backend='ascend', sampling_backend='pytorch', grammar_backend='xgrammar', radix_cache_backend=None, mm_attention_backend=None, fp8_gemm_runner_backend='auto', fp4_gemm_runner_backend='auto', dsa_prefill_backend=None, dsa_decode_backend=None, dsa_topk_backend='sgl-kernel', disable_flashinfer_autotune=False, mamba_backend='triton', speculative_algorithm=None, speculative_draft_model_path=None, speculative_draft_model_revision=None, speculative_draft_load_format=None, speculative_num_steps=None, speculative_eagle_topk=None, speculative_num_draft_tokens=None, speculative_dflash_block_size=None, speculative_accept_threshold_single=1.0, speculative_accept_threshold_acc=1.0, speculative_use_rejection_sampling=False, speculative_token_map=None, speculative_attention_mode='prefill', speculative_draft_attention_backend=None, speculative_draft_window_size=None, speculative_moe_runner_backend='auto', speculative_moe_a2a_backend=None, speculative_draft_model_quantization=None, speculative_skip_dp_mlp_sync=False, enable_multi_layer_eagle=False, speculative_adaptive=False, speculative_adaptive_config=None, decoupled_spec_bind_endpoint=None, decoupled_spec_connect_endpoints=None, decoupled_spec_rank=None, decoupled_spec_role='null', spec_trace_dir=None, speculative_ngram_min_bfs_breadth=1, speculative_ngram_max_bfs_breadth=10, speculative_ngram_match_type='BFS', speculative_ngram_max_trie_depth=18, speculative_ngram_capacity=10000000, speculative_ngram_external_corpus_path=None, speculative_ngram_external_sam_budget=0, speculative_ngram_external_corpus_max_tokens=10000000, ep_size=1, moe_a2a_backend='none', moe_runner_backend='auto', flashinfer_mxfp4_moe_precision='default', deepep_mode='auto', deepep_dispatcher_output_dtype='auto', ep_num_redundant_experts=0, ep_dispatch_algorithm=None, init_expert_location='trivial', enable_eplb=False, eplb_algorithm='auto', eplb_rebalance_num_iterations=1000, eplb_rebalance_layers_per_chunk=None, eplb_min_rebalancing_utilization_threshold=1.0, expert_distribution_recorder_mode=None, expert_distribution_recorder_buffer_size=1000, enable_expert_distribution_metrics=False, deepep_config=None, moe_dense_tp_size=None, elastic_ep_backend=None, enable_elastic_expert_backup=False, mooncake_ib_device=None, enable_deepep_waterfill=False, elastic_ep_rejoin=False, disable_flashinfer_cutlass_moe_fp4_allgather=False, disable_shared_experts_fusion=False, enforce_shared_experts_fusion=False, max_mamba_cache_size=None, mamba_ssm_dtype=None, enable_mamba_cache_stochastic_rounding=False, mamba_cache_philox_rounds=0, mamba_full_memory_ratio=0.9, mamba_radix_cache_strategy='auto', mamba_track_interval=256, enable_int8_mamba_checkpoint=False, int8_mamba_ckpt_size=None, linear_attn_backend='triton', linear_attn_decode_backend=None, linear_attn_prefill_backend=None, enable_linear_replayssm=False, linear_replayssm_cache_len=16, enable_hierarchical_cache=False, hicache_ratio=2.0, hicache_size=0, hicache_write_policy='write_through', hicache_io_backend='kernel', hicache_mem_layout='page_first', hicache_storage_backend=None, hicache_storage_prefetch_policy='timeout', hicache_storage_backend_extra_config=None, enable_hisparse=False, hisparse_config=None, enable_lmcache=False, lmcache_config_file=None, kt_weight_path=None, kt_method='AMXINT4', kt_cpuinfer=None, kt_threadpool_count=2, kt_num_gpu_experts=None, kt_max_deferred_experts_per_token=None, dllm_algorithm=None, dllm_algorithm_config=None, cpu_offload_gb=0, offload_group_size=-1, offload_num_in_group=1, offload_prefetch_step=1, offload_mode='cpu', cuda_graph_config=CudaGraphConfig(decode=PhaseConfig(backend='disabled', max_bs=256, bs=[1, 2, 4, 8, 12, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152, 160, 168, 176, 184, 192, 200, 208, 216, 224, 232, 240, 248, 256], tc_compiler='eager'), prefill=PhaseConfig(backend='disabled', max_bs=8192, bs=[4, 8, 12, 16, 20, 24, 28, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 208, 224, 240, 256, 288, 320, 352, 384, 416, 448, 480, 512, 576, 640, 704, 768, 832, 896, 960, 1024, 1280, 1536, 1792, 2048, 2304, 2560, 2816, 3072, 3328, 3584, 3840, 4096, 4608, 5120, 5632, 6144, 6656, 7168, 7680, 8192], tc_compiler='eager')), cuda_graph_backend_decode=None, cuda_graph_backend_prefill=None, cuda_graph_max_bs_decode=None, cuda_graph_max_bs_prefill=None, cuda_graph_bs_decode=None, cuda_graph_bs_prefill=None, cuda_graph_tc_compiler=None, disable_prefill_cuda_graph=False, disable_decode_cuda_graph=False, disable_cuda_graph=True, disable_cuda_graph_padding=False, enable_profile_cuda_graph=False, enable_cudagraph_gc=False, debug_cuda_graph=False, enable_layerwise_nvtx_marker=False, enable_nccl_nvls=False, enable_symm_mem=False, triton_attention_reduce_in_fp32=False, triton_attention_num_kv_splits=8, triton_attention_split_tile_size=None, flashinfer_mla_disable_ragged=False, enable_fused_qk_norm_rope=False, enable_precise_embedding_interpolation=False, enable_fused_moe_sum_all_reduce=False, enable_deepseek_v4_fp4_indexer=False, disable_custom_all_reduce=True, enable_mscclpp=False, enable_torch_symm_mem=False, pre_warm_nccl=False, enable_quant_communications=False, enable_flashinfer_allreduce_fusion=False, enforce_disable_flashinfer_allreduce_fusion=False, flashinfer_allreduce_fusion_backend=None, enable_aiter_allreduce_fusion=False, enable_two_batch_overlap=False, enable_single_batch_overlap=False, tbo_token_distribution_threshold=0.48, enable_torch_compile=False, enable_torch_compile_debug_mode=False, torch_compile_max_bs=32, torchao_config='', enable_memory_saver=False, enable_weights_cpu_backup=False, enable_draft_weights_cpu_backup=False, enable_custom_logit_processor=False, enable_return_hidden_states=False, enable_return_routed_experts=False, enable_return_indexer_topk=False, disable_outlines_disk_cache=False, enable_mis=False, enable_deterministic_inference=False, rl_on_policy_target=None, kv_canary='none', kv_canary_real_data='none', kv_canary_sweep_interval=0, enable_dynamic_batch_tokenizer=False, dynamic_batch_tokenizer_batch_size=32, dynamic_batch_tokenizer_batch_timeout=0.002, enable_tokenizer_batch_encode=False, disable_tokenizer_batch_decode=False, debug_tensor_dump_output_folder=None, debug_tensor_dump_layers=None, debug_tensor_dump_input_file=None, disaggregation_mode='null', disaggregation_transfer_backend='mooncake', disaggregation_bootstrap_port=8998, disaggregation_ib_device=None, disaggregation_decode_enable_radix_cache=False, disaggregation_decode_enable_offload_kvcache=False, num_reserved_decode_tokens=512, disaggregation_decode_extra_slots=None, disaggregation_decode_polling_interval=1, optimistic_prefill_retries=0, encoder_only=False, language_only=False, encoder_transfer_backend='zmq_to_scheduler', encoder_urls=[], encoder_bootstrap_port=8997, encoder_register_urls=[], enable_adaptive_dispatch_to_encoder=False, enable_pdmux=False, pdmux_config_path=None, sm_group_num=8, custom_weight_loader=[], weight_loader_disable_mmap=False, weight_loader_prefetch_checkpoints=False, weight_loader_prefetch_num_threads=4, weight_loader_drop_cache_after_load=False, remote_instance_weight_loader_seed_instance_ip=None, remote_instance_weight_loader_seed_instance_service_port=None, remote_instance_weight_loader_send_weights_group_ports=None, remote_instance_weight_loader_backend='nccl', remote_instance_weight_loader_start_seed_via_transfer_engine=False, engine_info_bootstrap_port=6789, modelexpress_config=None, download_dir=None, model_checksum=None, delete_ckpt_after_loading=False, decrypted_config_file=None, decrypted_draft_config_file=None, checkpoint_engine_wait_weights_before_ready=False, enable_broadcast_mm_inputs_process=False, enable_prefix_mm_cache=False, mm_enable_dp_encoder=False, mm_process_config={}, limit_mm_data_per_request=None, enable_mm_global_cache=False, disable_fast_image_processor=False, keep_mm_feature_on_device=False, forward_hooks=None, msprobe_dump_config=None)
[2026-07-01 15:18:37] Using default HuggingFace chat template with detected content format: string
[2026-07-01 15:18:37] Failed to load tokenizer vocab for template detection: 'TiktokenTokenizer' object has no attribute 'get_vocab'. Vocab-dependent detection rules will be skipped.
[2026-07-01 15:18:51 TP1] Failed to load generation config for /data/weights/grok-2: /data/weights/grok-2 does not appear to have a file named generation_config.json. Checkout 'https://huggingface.co//data/weights/grok-2/tree/main' for available files.. Proceeding without generation config.
[2026-07-01 15:18:51 TP4] Failed to load generation config for /data/weights/grok-2: /data/weights/grok-2 does not appear to have a file named generation_config.json. Checkout 'https://huggingface.co//data/weights/grok-2/tree/main' for available files.. Proceeding without generation config.
[2026-07-01 15:18:52 TP0] Failed to load generation config for /data/weights/grok-2: /data/weights/grok-2 does not appear to have a file named generation_config.json. Checkout 'https://huggingface.co//data/weights/grok-2/tree/main' for available files.. Proceeding without generation config.
[2026-07-01 15:18:52 TP1] NPU custom kernel packages unavailable: No module named 'custom_ops'
[2026-07-01 15:18:52 TP3] Failed to load generation config for /data/weights/grok-2: /data/weights/grok-2 does not appear to have a file named generation_config.json. Checkout 'https://huggingface.co//data/weights/grok-2/tree/main' for available files.. Proceeding without generation config.
[2026-07-01 15:18:52 TP6] Failed to load generation config for /data/weights/grok-2: /data/weights/grok-2 does not appear to have a file named generation_config.json. Checkout 'https://huggingface.co//data/weights/grok-2/tree/main' for available files.. Proceeding without generation config.
[2026-07-01 15:18:52 TP2] Failed to load generation config for /data/weights/grok-2: /data/weights/grok-2 does not appear to have a file named generation_config.json. Checkout 'https://huggingface.co//data/weights/grok-2/tree/main' for available files.. Proceeding without generation config.
[2026-07-01 15:18:52 TP4] NPU custom kernel packages unavailable: No module named 'custom_ops'
[2026-07-01 15:18:52 TP5] Failed to load generation config for /data/weights/grok-2: /data/weights/grok-2 does not appear to have a file named generation_config.json. Checkout 'https://huggingface.co//data/weights/grok-2/tree/main' for available files.. Proceeding without generation config.
[2026-07-01 15:18:52 TP0] NPU custom kernel packages unavailable: No module named 'custom_ops'
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:362: ImportWarning: 
    *************************************************************************************************************
    The torch.Tensor.cuda and torch.nn.Module.cuda are replaced with torch.Tensor.npu and torch.nn.Module.npu now..
    The torch.cuda.DoubleTensor is replaced with torch.npu.FloatTensor cause the double type is not supported now..
    The backend in torch.distributed.init_process_group set to hccl now..
    The torch.cuda.* and torch.cuda.amp.* are replaced with torch.npu.* and torch.npu.amp.* now..
    The device parameters have been replaced with npu in the function below:
    torch.logspace, torch.randint, torch.hann_window, torch.rand, torch.full_like, torch.ones_like, torch.rand_like, torch.randperm, torch.arange, torch.frombuffer, torch.normal, torch._empty_per_channel_affine_quantized, torch.empty_strided, torch.empty_like, torch.scalar_tensor, torch.tril_indices, torch.bartlett_window, torch.ones, torch.sparse_coo_tensor, torch.randn, torch.kaiser_window, torch.tensor, torch.triu_indices, torch.as_tensor, torch.zeros, torch.randint_like, torch.full, torch.eye, torch._sparse_csr_tensor_unsafe, torch.empty, torch._sparse_coo_tensor_unsafe, torch.blackman_window, torch.zeros_like, torch.range, torch.sparse_csr_tensor, torch.randn_like, torch.from_file, torch._cudnn_init_dropout_state, torch._empty_affine_quantized, torch.linspace, torch.hamming_window, torch.empty_quantized, torch._pin_memory, torch.load, torch.set_default_device, torch.get_device_module, torch.sparse_compressed_tensor, torch.Tensor.new_empty, torch.Tensor.new_empty_strided, torch.Tensor.new_full, torch.Tensor.new_ones, torch.Tensor.new_tensor, torch.Tensor.new_zeros, torch.Tensor.to, torch.Tensor.pin_memory, torch.nn.Module.to, torch.nn.Module.to_empty
    *************************************************************************************************************
    
  warnings.warn(msg, ImportWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:291: RuntimeWarning: torch.jit.script and torch.jit.script_method will be disabled by transfer_to_npu, which currently does not support them, if you need to enable them, please do not use transfer_to_npu.
  warnings.warn(msg, RuntimeWarning)
[2026-07-01 15:18:53 TP7] Failed to load generation config for /data/weights/grok-2: /data/weights/grok-2 does not appear to have a file named generation_config.json. Checkout 'https://huggingface.co//data/weights/grok-2/tree/main' for available files.. Proceeding without generation config.
[2026-07-01 15:18:53 TP8] Failed to load generation config for /data/weights/grok-2: /data/weights/grok-2 does not appear to have a file named generation_config.json. Checkout 'https://huggingface.co//data/weights/grok-2/tree/main' for available files.. Proceeding without generation config.
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:362: ImportWarning: 
    *************************************************************************************************************
    The torch.Tensor.cuda and torch.nn.Module.cuda are replaced with torch.Tensor.npu and torch.nn.Module.npu now..
    The torch.cuda.DoubleTensor is replaced with torch.npu.FloatTensor cause the double type is not supported now..
    The backend in torch.distributed.init_process_group set to hccl now..
    The torch.cuda.* and torch.cuda.amp.* are replaced with torch.npu.* and torch.npu.amp.* now..
    The device parameters have been replaced with npu in the function below:
    torch.logspace, torch.randint, torch.hann_window, torch.rand, torch.full_like, torch.ones_like, torch.rand_like, torch.randperm, torch.arange, torch.frombuffer, torch.normal, torch._empty_per_channel_affine_quantized, torch.empty_strided, torch.empty_like, torch.scalar_tensor, torch.tril_indices, torch.bartlett_window, torch.ones, torch.sparse_coo_tensor, torch.randn, torch.kaiser_window, torch.tensor, torch.triu_indices, torch.as_tensor, torch.zeros, torch.randint_like, torch.full, torch.eye, torch._sparse_csr_tensor_unsafe, torch.empty, torch._sparse_coo_tensor_unsafe, torch.blackman_window, torch.zeros_like, torch.range, torch.sparse_csr_tensor, torch.randn_like, torch.from_file, torch._cudnn_init_dropout_state, torch._empty_affine_quantized, torch.linspace, torch.hamming_window, torch.empty_quantized, torch._pin_memory, torch.load, torch.set_default_device, torch.get_device_module, torch.sparse_compressed_tensor, torch.Tensor.new_empty, torch.Tensor.new_empty_strided, torch.Tensor.new_full, torch.Tensor.new_ones, torch.Tensor.new_tensor, torch.Tensor.new_zeros, torch.Tensor.to, torch.Tensor.pin_memory, torch.nn.Module.to, torch.nn.Module.to_empty
    *************************************************************************************************************
    
  warnings.warn(msg, ImportWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:291: RuntimeWarning: torch.jit.script and torch.jit.script_method will be disabled by transfer_to_npu, which currently does not support them, if you need to enable them, please do not use transfer_to_npu.
  warnings.warn(msg, RuntimeWarning)
[2026-07-01 15:18:53 TP3] NPU custom kernel packages unavailable: No module named 'custom_ops'
[2026-07-01 15:18:53 TP14] Failed to load generation config for /data/weights/grok-2: /data/weights/grok-2 does not appear to have a file named generation_config.json. Checkout 'https://huggingface.co//data/weights/grok-2/tree/main' for available files.. Proceeding without generation config.
[2026-07-01 15:18:53 TP1] Init torch distributed begin.
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:362: ImportWarning: 
    *************************************************************************************************************
    The torch.Tensor.cuda and torch.nn.Module.cuda are replaced with torch.Tensor.npu and torch.nn.Module.npu now..
    The torch.cuda.DoubleTensor is replaced with torch.npu.FloatTensor cause the double type is not supported now..
    The backend in torch.distributed.init_process_group set to hccl now..
    The torch.cuda.* and torch.cuda.amp.* are replaced with torch.npu.* and torch.npu.amp.* now..
    The device parameters have been replaced with npu in the function below:
    torch.logspace, torch.randint, torch.hann_window, torch.rand, torch.full_like, torch.ones_like, torch.rand_like, torch.randperm, torch.arange, torch.frombuffer, torch.normal, torch._empty_per_channel_affine_quantized, torch.empty_strided, torch.empty_like, torch.scalar_tensor, torch.tril_indices, torch.bartlett_window, torch.ones, torch.sparse_coo_tensor, torch.randn, torch.kaiser_window, torch.tensor, torch.triu_indices, torch.as_tensor, torch.zeros, torch.randint_like, torch.full, torch.eye, torch._sparse_csr_tensor_unsafe, torch.empty, torch._sparse_coo_tensor_unsafe, torch.blackman_window, torch.zeros_like, torch.range, torch.sparse_csr_tensor, torch.randn_like, torch.from_file, torch._cudnn_init_dropout_state, torch._empty_affine_quantized, torch.linspace, torch.hamming_window, torch.empty_quantized, torch._pin_memory, torch.load, torch.set_default_device, torch.get_device_module, torch.sparse_compressed_tensor, torch.Tensor.new_empty, torch.Tensor.new_empty_strided, torch.Tensor.new_full, torch.Tensor.new_ones, torch.Tensor.new_tensor, torch.Tensor.new_zeros, torch.Tensor.to, torch.Tensor.pin_memory, torch.nn.Module.to, torch.nn.Module.to_empty
    *************************************************************************************************************
    
  warnings.warn(msg, ImportWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:291: RuntimeWarning: torch.jit.script and torch.jit.script_method will be disabled by transfer_to_npu, which currently does not support them, if you need to enable them, please do not use transfer_to_npu.
  warnings.warn(msg, RuntimeWarning)
[2026-07-01 15:18:53 TP6] NPU custom kernel packages unavailable: No module named 'custom_ops'
[2026-07-01 15:18:53 TP2] NPU custom kernel packages unavailable: No module named 'custom_ops'
[2026-07-01 15:18:53 TP4] Init torch distributed begin.
[2026-07-01 15:18:53 TP5] NPU custom kernel packages unavailable: No module named 'custom_ops'
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:362: ImportWarning: 
    *************************************************************************************************************
    The torch.Tensor.cuda and torch.nn.Module.cuda are replaced with torch.Tensor.npu and torch.nn.Module.npu now..
    The torch.cuda.DoubleTensor is replaced with torch.npu.FloatTensor cause the double type is not supported now..
    The backend in torch.distributed.init_process_group set to hccl now..
    The torch.cuda.* and torch.cuda.amp.* are replaced with torch.npu.* and torch.npu.amp.* now..
    The device parameters have been replaced with npu in the function below:
    torch.logspace, torch.randint, torch.hann_window, torch.rand, torch.full_like, torch.ones_like, torch.rand_like, torch.randperm, torch.arange, torch.frombuffer, torch.normal, torch._empty_per_channel_affine_quantized, torch.empty_strided, torch.empty_like, torch.scalar_tensor, torch.tril_indices, torch.bartlett_window, torch.ones, torch.sparse_coo_tensor, torch.randn, torch.kaiser_window, torch.tensor, torch.triu_indices, torch.as_tensor, torch.zeros, torch.randint_like, torch.full, torch.eye, torch._sparse_csr_tensor_unsafe, torch.empty, torch._sparse_coo_tensor_unsafe, torch.blackman_window, torch.zeros_like, torch.range, torch.sparse_csr_tensor, torch.randn_like, torch.from_file, torch._cudnn_init_dropout_state, torch._empty_affine_quantized, torch.linspace, torch.hamming_window, torch.empty_quantized, torch._pin_memory, torch.load, torch.set_default_device, torch.get_device_module, torch.sparse_compressed_tensor, torch.Tensor.new_empty, torch.Tensor.new_empty_strided, torch.Tensor.new_full, torch.Tensor.new_ones, torch.Tensor.new_tensor, torch.Tensor.new_zeros, torch.Tensor.to, torch.Tensor.pin_memory, torch.nn.Module.to, torch.nn.Module.to_empty
    *************************************************************************************************************
    
  warnings.warn(msg, ImportWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:291: RuntimeWarning: torch.jit.script and torch.jit.script_method will be disabled by transfer_to_npu, which currently does not support them, if you need to enable them, please do not use transfer_to_npu.
  warnings.warn(msg, RuntimeWarning)
[2026-07-01 15:18:53 TP15] Failed to load generation config for /data/weights/grok-2: /data/weights/grok-2 does not appear to have a file named generation_config.json. Checkout 'https://huggingface.co//data/weights/grok-2/tree/main' for available files.. Proceeding without generation config.
[2026-07-01 15:18:53 TP8] NPU custom kernel packages unavailable: No module named 'custom_ops'
[2026-07-01 15:18:53 TP9] Failed to load generation config for /data/weights/grok-2: /data/weights/grok-2 does not appear to have a file named generation_config.json. Checkout 'https://huggingface.co//data/weights/grok-2/tree/main' for available files.. Proceeding without generation config.
[2026-07-01 15:18:53 TP0] Init torch distributed begin.
[2026-07-01 15:18:53 TP11] Failed to load generation config for /data/weights/grok-2: /data/weights/grok-2 does not appear to have a file named generation_config.json. Checkout 'https://huggingface.co//data/weights/grok-2/tree/main' for available files.. Proceeding without generation config.
[2026-07-01 15:18:53 TP7] NPU custom kernel packages unavailable: No module named 'custom_ops'
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:362: ImportWarning: 
    *************************************************************************************************************
    The torch.Tensor.cuda and torch.nn.Module.cuda are replaced with torch.Tensor.npu and torch.nn.Module.npu now..
    The torch.cuda.DoubleTensor is replaced with torch.npu.FloatTensor cause the double type is not supported now..
    The backend in torch.distributed.init_process_group set to hccl now..
    The torch.cuda.* and torch.cuda.amp.* are replaced with torch.npu.* and torch.npu.amp.* now..
    The device parameters have been replaced with npu in the function below:
    torch.logspace, torch.randint, torch.hann_window, torch.rand, torch.full_like, torch.ones_like, torch.rand_like, torch.randperm, torch.arange, torch.frombuffer, torch.normal, torch._empty_per_channel_affine_quantized, torch.empty_strided, torch.empty_like, torch.scalar_tensor, torch.tril_indices, torch.bartlett_window, torch.ones, torch.sparse_coo_tensor, torch.randn, torch.kaiser_window, torch.tensor, torch.triu_indices, torch.as_tensor, torch.zeros, torch.randint_like, torch.full, torch.eye, torch._sparse_csr_tensor_unsafe, torch.empty, torch._sparse_coo_tensor_unsafe, torch.blackman_window, torch.zeros_like, torch.range, torch.sparse_csr_tensor, torch.randn_like, torch.from_file, torch._cudnn_init_dropout_state, torch._empty_affine_quantized, torch.linspace, torch.hamming_window, torch.empty_quantized, torch._pin_memory, torch.load, torch.set_default_device, torch.get_device_module, torch.sparse_compressed_tensor, torch.Tensor.new_empty, torch.Tensor.new_empty_strided, torch.Tensor.new_full, torch.Tensor.new_ones, torch.Tensor.new_tensor, torch.Tensor.new_zeros, torch.Tensor.to, torch.Tensor.pin_memory, torch.nn.Module.to, torch.nn.Module.to_empty
    *************************************************************************************************************
    
  warnings.warn(msg, ImportWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:291: RuntimeWarning: torch.jit.script and torch.jit.script_method will be disabled by transfer_to_npu, which currently does not support them, if you need to enable them, please do not use transfer_to_npu.
  warnings.warn(msg, RuntimeWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:362: ImportWarning: 
    *************************************************************************************************************
    The torch.Tensor.cuda and torch.nn.Module.cuda are replaced with torch.Tensor.npu and torch.nn.Module.npu now..
    The torch.cuda.DoubleTensor is replaced with torch.npu.FloatTensor cause the double type is not supported now..
    The backend in torch.distributed.init_process_group set to hccl now..
    The torch.cuda.* and torch.cuda.amp.* are replaced with torch.npu.* and torch.npu.amp.* now..
    The device parameters have been replaced with npu in the function below:
    torch.logspace, torch.randint, torch.hann_window, torch.rand, torch.full_like, torch.ones_like, torch.rand_like, torch.randperm, torch.arange, torch.frombuffer, torch.normal, torch._empty_per_channel_affine_quantized, torch.empty_strided, torch.empty_like, torch.scalar_tensor, torch.tril_indices, torch.bartlett_window, torch.ones, torch.sparse_coo_tensor, torch.randn, torch.kaiser_window, torch.tensor, torch.triu_indices, torch.as_tensor, torch.zeros, torch.randint_like, torch.full, torch.eye, torch._sparse_csr_tensor_unsafe, torch.empty, torch._sparse_coo_tensor_unsafe, torch.blackman_window, torch.zeros_like, torch.range, torch.sparse_csr_tensor, torch.randn_like, torch.from_file, torch._cudnn_init_dropout_state, torch._empty_affine_quantized, torch.linspace, torch.hamming_window, torch.empty_quantized, torch._pin_memory, torch.load, torch.set_default_device, torch.get_device_module, torch.sparse_compressed_tensor, torch.Tensor.new_empty, torch.Tensor.new_empty_strided, torch.Tensor.new_full, torch.Tensor.new_ones, torch.Tensor.new_tensor, torch.Tensor.new_zeros, torch.Tensor.to, torch.Tensor.pin_memory, torch.nn.Module.to, torch.nn.Module.to_empty
    *************************************************************************************************************
    
  warnings.warn(msg, ImportWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:291: RuntimeWarning: torch.jit.script and torch.jit.script_method will be disabled by transfer_to_npu, which currently does not support them, if you need to enable them, please do not use transfer_to_npu.
  warnings.warn(msg, RuntimeWarning)
[2026-07-01 15:18:54 TP10] Failed to load generation config for /data/weights/grok-2: /data/weights/grok-2 does not appear to have a file named generation_config.json. Checkout 'https://huggingface.co//data/weights/grok-2/tree/main' for available files.. Proceeding without generation config.
[2026-07-01 15:18:54 TP3] Init torch distributed begin.
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:362: ImportWarning: 
    *************************************************************************************************************
    The torch.Tensor.cuda and torch.nn.Module.cuda are replaced with torch.Tensor.npu and torch.nn.Module.npu now..
    The torch.cuda.DoubleTensor is replaced with torch.npu.FloatTensor cause the double type is not supported now..
    The backend in torch.distributed.init_process_group set to hccl now..
    The torch.cuda.* and torch.cuda.amp.* are replaced with torch.npu.* and torch.npu.amp.* now..
    The device parameters have been replaced with npu in the function below:
    torch.logspace, torch.randint, torch.hann_window, torch.rand, torch.full_like, torch.ones_like, torch.rand_like, torch.randperm, torch.arange, torch.frombuffer, torch.normal, torch._empty_per_channel_affine_quantized, torch.empty_strided, torch.empty_like, torch.scalar_tensor, torch.tril_indices, torch.bartlett_window, torch.ones, torch.sparse_coo_tensor, torch.randn, torch.kaiser_window, torch.tensor, torch.triu_indices, torch.as_tensor, torch.zeros, torch.randint_like, torch.full, torch.eye, torch._sparse_csr_tensor_unsafe, torch.empty, torch._sparse_coo_tensor_unsafe, torch.blackman_window, torch.zeros_like, torch.range, torch.sparse_csr_tensor, torch.randn_like, torch.from_file, torch._cudnn_init_dropout_state, torch._empty_affine_quantized, torch.linspace, torch.hamming_window, torch.empty_quantized, torch._pin_memory, torch.load, torch.set_default_device, torch.get_device_module, torch.sparse_compressed_tensor, torch.Tensor.new_empty, torch.Tensor.new_empty_strided, torch.Tensor.new_full, torch.Tensor.new_ones, torch.Tensor.new_tensor, torch.Tensor.new_zeros, torch.Tensor.to, torch.Tensor.pin_memory, torch.nn.Module.to, torch.nn.Module.to_empty
    *************************************************************************************************************
    
  warnings.warn(msg, ImportWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:291: RuntimeWarning: torch.jit.script and torch.jit.script_method will be disabled by transfer_to_npu, which currently does not support them, if you need to enable them, please do not use transfer_to_npu.
  warnings.warn(msg, RuntimeWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:362: ImportWarning: 
    *************************************************************************************************************
    The torch.Tensor.cuda and torch.nn.Module.cuda are replaced with torch.Tensor.npu and torch.nn.Module.npu now..
    The torch.cuda.DoubleTensor is replaced with torch.npu.FloatTensor cause the double type is not supported now..
    The backend in torch.distributed.init_process_group set to hccl now..
    The torch.cuda.* and torch.cuda.amp.* are replaced with torch.npu.* and torch.npu.amp.* now..
    The device parameters have been replaced with npu in the function below:
    torch.logspace, torch.randint, torch.hann_window, torch.rand, torch.full_like, torch.ones_like, torch.rand_like, torch.randperm, torch.arange, torch.frombuffer, torch.normal, torch._empty_per_channel_affine_quantized, torch.empty_strided, torch.empty_like, torch.scalar_tensor, torch.tril_indices, torch.bartlett_window, torch.ones, torch.sparse_coo_tensor, torch.randn, torch.kaiser_window, torch.tensor, torch.triu_indices, torch.as_tensor, torch.zeros, torch.randint_like, torch.full, torch.eye, torch._sparse_csr_tensor_unsafe, torch.empty, torch._sparse_coo_tensor_unsafe, torch.blackman_window, torch.zeros_like, torch.range, torch.sparse_csr_tensor, torch.randn_like, torch.from_file, torch._cudnn_init_dropout_state, torch._empty_affine_quantized, torch.linspace, torch.hamming_window, torch.empty_quantized, torch._pin_memory, torch.load, torch.set_default_device, torch.get_device_module, torch.sparse_compressed_tensor, torch.Tensor.new_empty, torch.Tensor.new_empty_strided, torch.Tensor.new_full, torch.Tensor.new_ones, torch.Tensor.new_tensor, torch.Tensor.new_zeros, torch.Tensor.to, torch.Tensor.pin_memory, torch.nn.Module.to, torch.nn.Module.to_empty
    *************************************************************************************************************
    
  warnings.warn(msg, ImportWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:291: RuntimeWarning: torch.jit.script and torch.jit.script_method will be disabled by transfer_to_npu, which currently does not support them, if you need to enable them, please do not use transfer_to_npu.
  warnings.warn(msg, RuntimeWarning)
[2026-07-01 15:18:54 TP14] NPU custom kernel packages unavailable: No module named 'custom_ops'
[2026-07-01 15:18:54 TP13] Failed to load generation config for /data/weights/grok-2: /data/weights/grok-2 does not appear to have a file named generation_config.json. Checkout 'https://huggingface.co//data/weights/grok-2/tree/main' for available files.. Proceeding without generation config.
[2026-07-01 15:18:54 TP12] Failed to load generation config for /data/weights/grok-2: /data/weights/grok-2 does not appear to have a file named generation_config.json. Checkout 'https://huggingface.co//data/weights/grok-2/tree/main' for available files.. Proceeding without generation config.
[2026-07-01 15:18:54 TP1] get env HCCL_BUFFSIZE = 200
[W701 15:18:54.053980993 socket.cpp:207] [c10d] The hostname of the client socket cannot be retrieved. err=-3
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:362: ImportWarning: 
    *************************************************************************************************************
    The torch.Tensor.cuda and torch.nn.Module.cuda are replaced with torch.Tensor.npu and torch.nn.Module.npu now..
    The torch.cuda.DoubleTensor is replaced with torch.npu.FloatTensor cause the double type is not supported now..
    The backend in torch.distributed.init_process_group set to hccl now..
    The torch.cuda.* and torch.cuda.amp.* are replaced with torch.npu.* and torch.npu.amp.* now..
    The device parameters have been replaced with npu in the function below:
    torch.logspace, torch.randint, torch.hann_window, torch.rand, torch.full_like, torch.ones_like, torch.rand_like, torch.randperm, torch.arange, torch.frombuffer, torch.normal, torch._empty_per_channel_affine_quantized, torch.empty_strided, torch.empty_like, torch.scalar_tensor, torch.tril_indices, torch.bartlett_window, torch.ones, torch.sparse_coo_tensor, torch.randn, torch.kaiser_window, torch.tensor, torch.triu_indices, torch.as_tensor, torch.zeros, torch.randint_like, torch.full, torch.eye, torch._sparse_csr_tensor_unsafe, torch.empty, torch._sparse_coo_tensor_unsafe, torch.blackman_window, torch.zeros_like, torch.range, torch.sparse_csr_tensor, torch.randn_like, torch.from_file, torch._cudnn_init_dropout_state, torch._empty_affine_quantized, torch.linspace, torch.hamming_window, torch.empty_quantized, torch._pin_memory, torch.load, torch.set_default_device, torch.get_device_module, torch.sparse_compressed_tensor, torch.Tensor.new_empty, torch.Tensor.new_empty_strided, torch.Tensor.new_full, torch.Tensor.new_ones, torch.Tensor.new_tensor, torch.Tensor.new_zeros, torch.Tensor.to, torch.Tensor.pin_memory, torch.nn.Module.to, torch.nn.Module.to_empty
    *************************************************************************************************************
    
  warnings.warn(msg, ImportWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:291: RuntimeWarning: torch.jit.script and torch.jit.script_method will be disabled by transfer_to_npu, which currently does not support them, if you need to enable them, please do not use transfer_to_npu.
  warnings.warn(msg, RuntimeWarning)
[2026-07-01 15:18:54 TP6] Init torch distributed begin.
[2026-07-01 15:18:54 TP2] Init torch distributed begin.
[2026-07-01 15:18:54 TP4] get env HCCL_BUFFSIZE = 200
[W701 15:18:54.202058398 socket.cpp:207] [c10d] The hostname of the client socket cannot be retrieved. err=-3
[2026-07-01 15:18:54 TP8] Init torch distributed begin.
[2026-07-01 15:18:54 TP15] NPU custom kernel packages unavailable: No module named 'custom_ops'
[2026-07-01 15:18:54 TP9] NPU custom kernel packages unavailable: No module named 'custom_ops'
[2026-07-01 15:18:54 TP5] Init torch distributed begin.
[2026-07-01 15:18:54 TP11] NPU custom kernel packages unavailable: No module named 'custom_ops'
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:362: ImportWarning: 
    *************************************************************************************************************
    The torch.Tensor.cuda and torch.nn.Module.cuda are replaced with torch.Tensor.npu and torch.nn.Module.npu now..
    The torch.cuda.DoubleTensor is replaced with torch.npu.FloatTensor cause the double type is not supported now..
    The backend in torch.distributed.init_process_group set to hccl now..
    The torch.cuda.* and torch.cuda.amp.* are replaced with torch.npu.* and torch.npu.amp.* now..
    The device parameters have been replaced with npu in the function below:
    torch.logspace, torch.randint, torch.hann_window, torch.rand, torch.full_like, torch.ones_like, torch.rand_like, torch.randperm, torch.arange, torch.frombuffer, torch.normal, torch._empty_per_channel_affine_quantized, torch.empty_strided, torch.empty_like, torch.scalar_tensor, torch.tril_indices, torch.bartlett_window, torch.ones, torch.sparse_coo_tensor, torch.randn, torch.kaiser_window, torch.tensor, torch.triu_indices, torch.as_tensor, torch.zeros, torch.randint_like, torch.full, torch.eye, torch._sparse_csr_tensor_unsafe, torch.empty, torch._sparse_coo_tensor_unsafe, torch.blackman_window, torch.zeros_like, torch.range, torch.sparse_csr_tensor, torch.randn_like, torch.from_file, torch._cudnn_init_dropout_state, torch._empty_affine_quantized, torch.linspace, torch.hamming_window, torch.empty_quantized, torch._pin_memory, torch.load, torch.set_default_device, torch.get_device_module, torch.sparse_compressed_tensor, torch.Tensor.new_empty, torch.Tensor.new_empty_strided, torch.Tensor.new_full, torch.Tensor.new_ones, torch.Tensor.new_tensor, torch.Tensor.new_zeros, torch.Tensor.to, torch.Tensor.pin_memory, torch.nn.Module.to, torch.nn.Module.to_empty
    *************************************************************************************************************
    
  warnings.warn(msg, ImportWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:291: RuntimeWarning: torch.jit.script and torch.jit.script_method will be disabled by transfer_to_npu, which currently does not support them, if you need to enable them, please do not use transfer_to_npu.
  warnings.warn(msg, RuntimeWarning)
[2026-07-01 15:18:54 TP10] NPU custom kernel packages unavailable: No module named 'custom_ops'
[2026-07-01 15:18:54 TP0] get env HCCL_BUFFSIZE = 200
[W701 15:18:54.511503553 socket.cpp:207] [c10d] The hostname of the client socket cannot be retrieved. err=-3
[2026-07-01 15:18:54 TP7] Init torch distributed begin.
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:362: ImportWarning: 
    *************************************************************************************************************
    The torch.Tensor.cuda and torch.nn.Module.cuda are replaced with torch.Tensor.npu and torch.nn.Module.npu now..
    The torch.cuda.DoubleTensor is replaced with torch.npu.FloatTensor cause the double type is not supported now..
    The backend in torch.distributed.init_process_group set to hccl now..
    The torch.cuda.* and torch.cuda.amp.* are replaced with torch.npu.* and torch.npu.amp.* now..
    The device parameters have been replaced with npu in the function below:
    torch.logspace, torch.randint, torch.hann_window, torch.rand, torch.full_like, torch.ones_like, torch.rand_like, torch.randperm, torch.arange, torch.frombuffer, torch.normal, torch._empty_per_channel_affine_quantized, torch.empty_strided, torch.empty_like, torch.scalar_tensor, torch.tril_indices, torch.bartlett_window, torch.ones, torch.sparse_coo_tensor, torch.randn, torch.kaiser_window, torch.tensor, torch.triu_indices, torch.as_tensor, torch.zeros, torch.randint_like, torch.full, torch.eye, torch._sparse_csr_tensor_unsafe, torch.empty, torch._sparse_coo_tensor_unsafe, torch.blackman_window, torch.zeros_like, torch.range, torch.sparse_csr_tensor, torch.randn_like, torch.from_file, torch._cudnn_init_dropout_state, torch._empty_affine_quantized, torch.linspace, torch.hamming_window, torch.empty_quantized, torch._pin_memory, torch.load, torch.set_default_device, torch.get_device_module, torch.sparse_compressed_tensor, torch.Tensor.new_empty, torch.Tensor.new_empty_strided, torch.Tensor.new_full, torch.Tensor.new_ones, torch.Tensor.new_tensor, torch.Tensor.new_zeros, torch.Tensor.to, torch.Tensor.pin_memory, torch.nn.Module.to, torch.nn.Module.to_empty
    *************************************************************************************************************
    
  warnings.warn(msg, ImportWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:291: RuntimeWarning: torch.jit.script and torch.jit.script_method will be disabled by transfer_to_npu, which currently does not support them, if you need to enable them, please do not use transfer_to_npu.
  warnings.warn(msg, RuntimeWarning)
[2026-07-01 15:18:55 TP3] get env HCCL_BUFFSIZE = 200
[W701 15:18:55.763463081 socket.cpp:207] [c10d] The hostname of the client socket cannot be retrieved. err=-3
[2026-07-01 15:18:55 TP13] NPU custom kernel packages unavailable: No module named 'custom_ops'
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:362: ImportWarning: 
    *************************************************************************************************************
    The torch.Tensor.cuda and torch.nn.Module.cuda are replaced with torch.Tensor.npu and torch.nn.Module.npu now..
    The torch.cuda.DoubleTensor is replaced with torch.npu.FloatTensor cause the double type is not supported now..
    The backend in torch.distributed.init_process_group set to hccl now..
    The torch.cuda.* and torch.cuda.amp.* are replaced with torch.npu.* and torch.npu.amp.* now..
    The device parameters have been replaced with npu in the function below:
    torch.logspace, torch.randint, torch.hann_window, torch.rand, torch.full_like, torch.ones_like, torch.rand_like, torch.randperm, torch.arange, torch.frombuffer, torch.normal, torch._empty_per_channel_affine_quantized, torch.empty_strided, torch.empty_like, torch.scalar_tensor, torch.tril_indices, torch.bartlett_window, torch.ones, torch.sparse_coo_tensor, torch.randn, torch.kaiser_window, torch.tensor, torch.triu_indices, torch.as_tensor, torch.zeros, torch.randint_like, torch.full, torch.eye, torch._sparse_csr_tensor_unsafe, torch.empty, torch._sparse_coo_tensor_unsafe, torch.blackman_window, torch.zeros_like, torch.range, torch.sparse_csr_tensor, torch.randn_like, torch.from_file, torch._cudnn_init_dropout_state, torch._empty_affine_quantized, torch.linspace, torch.hamming_window, torch.empty_quantized, torch._pin_memory, torch.load, torch.set_default_device, torch.get_device_module, torch.sparse_compressed_tensor, torch.Tensor.new_empty, torch.Tensor.new_empty_strided, torch.Tensor.new_full, torch.Tensor.new_ones, torch.Tensor.new_tensor, torch.Tensor.new_zeros, torch.Tensor.to, torch.Tensor.pin_memory, torch.nn.Module.to, torch.nn.Module.to_empty
    *************************************************************************************************************
    
  warnings.warn(msg, ImportWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:291: RuntimeWarning: torch.jit.script and torch.jit.script_method will be disabled by transfer_to_npu, which currently does not support them, if you need to enable them, please do not use transfer_to_npu.
  warnings.warn(msg, RuntimeWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:362: ImportWarning: 
    *************************************************************************************************************
    The torch.Tensor.cuda and torch.nn.Module.cuda are replaced with torch.Tensor.npu and torch.nn.Module.npu now..
    The torch.cuda.DoubleTensor is replaced with torch.npu.FloatTensor cause the double type is not supported now..
    The backend in torch.distributed.init_process_group set to hccl now..
    The torch.cuda.* and torch.cuda.amp.* are replaced with torch.npu.* and torch.npu.amp.* now..
    The device parameters have been replaced with npu in the function below:
    torch.logspace, torch.randint, torch.hann_window, torch.rand, torch.full_like, torch.ones_like, torch.rand_like, torch.randperm, torch.arange, torch.frombuffer, torch.normal, torch._empty_per_channel_affine_quantized, torch.empty_strided, torch.empty_like, torch.scalar_tensor, torch.tril_indices, torch.bartlett_window, torch.ones, torch.sparse_coo_tensor, torch.randn, torch.kaiser_window, torch.tensor, torch.triu_indices, torch.as_tensor, torch.zeros, torch.randint_like, torch.full, torch.eye, torch._sparse_csr_tensor_unsafe, torch.empty, torch._sparse_coo_tensor_unsafe, torch.blackman_window, torch.zeros_like, torch.range, torch.sparse_csr_tensor, torch.randn_like, torch.from_file, torch._cudnn_init_dropout_state, torch._empty_affine_quantized, torch.linspace, torch.hamming_window, torch.empty_quantized, torch._pin_memory, torch.load, torch.set_default_device, torch.get_device_module, torch.sparse_compressed_tensor, torch.Tensor.new_empty, torch.Tensor.new_empty_strided, torch.Tensor.new_full, torch.Tensor.new_ones, torch.Tensor.new_tensor, torch.Tensor.new_zeros, torch.Tensor.to, torch.Tensor.pin_memory, torch.nn.Module.to, torch.nn.Module.to_empty
    *************************************************************************************************************
    
  warnings.warn(msg, ImportWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:291: RuntimeWarning: torch.jit.script and torch.jit.script_method will be disabled by transfer_to_npu, which currently does not support them, if you need to enable them, please do not use transfer_to_npu.
  warnings.warn(msg, RuntimeWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:362: ImportWarning: 
    *************************************************************************************************************
    The torch.Tensor.cuda and torch.nn.Module.cuda are replaced with torch.Tensor.npu and torch.nn.Module.npu now..
    The torch.cuda.DoubleTensor is replaced with torch.npu.FloatTensor cause the double type is not supported now..
    The backend in torch.distributed.init_process_group set to hccl now..
    The torch.cuda.* and torch.cuda.amp.* are replaced with torch.npu.* and torch.npu.amp.* now..
    The device parameters have been replaced with npu in the function below:
    torch.logspace, torch.randint, torch.hann_window, torch.rand, torch.full_like, torch.ones_like, torch.rand_like, torch.randperm, torch.arange, torch.frombuffer, torch.normal, torch._empty_per_channel_affine_quantized, torch.empty_strided, torch.empty_like, torch.scalar_tensor, torch.tril_indices, torch.bartlett_window, torch.ones, torch.sparse_coo_tensor, torch.randn, torch.kaiser_window, torch.tensor, torch.triu_indices, torch.as_tensor, torch.zeros, torch.randint_like, torch.full, torch.eye, torch._sparse_csr_tensor_unsafe, torch.empty, torch._sparse_coo_tensor_unsafe, torch.blackman_window, torch.zeros_like, torch.range, torch.sparse_csr_tensor, torch.randn_like, torch.from_file, torch._cudnn_init_dropout_state, torch._empty_affine_quantized, torch.linspace, torch.hamming_window, torch.empty_quantized, torch._pin_memory, torch.load, torch.set_default_device, torch.get_device_module, torch.sparse_compressed_tensor, torch.Tensor.new_empty, torch.Tensor.new_empty_strided, torch.Tensor.new_full, torch.Tensor.new_ones, torch.Tensor.new_tensor, torch.Tensor.new_zeros, torch.Tensor.to, torch.Tensor.pin_memory, torch.nn.Module.to, torch.nn.Module.to_empty
    *************************************************************************************************************
    
  warnings.warn(msg, ImportWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:291: RuntimeWarning: torch.jit.script and torch.jit.script_method will be disabled by transfer_to_npu, which currently does not support them, if you need to enable them, please do not use transfer_to_npu.
  warnings.warn(msg, RuntimeWarning)
[2026-07-01 15:18:55 TP14] Init torch distributed begin.
[2026-07-01 15:18:55 TP12] NPU custom kernel packages unavailable: No module named 'custom_ops'
[2026-07-01 15:18:55 TP6] get env HCCL_BUFFSIZE = 200
[W701 15:18:55.048059277 socket.cpp:207] [c10d] The hostname of the client socket cannot be retrieved. err=-3
[2026-07-01 15:18:55 TP9] Init torch distributed begin.
[2026-07-01 15:18:55 TP8] get env HCCL_BUFFSIZE = 200
[W701 15:18:55.201581387 socket.cpp:207] [c10d] The hostname of the client socket cannot be retrieved. err=-3
[2026-07-01 15:18:55 TP2] get env HCCL_BUFFSIZE = 200
[W701 15:18:55.210946511 socket.cpp:207] [c10d] The hostname of the client socket cannot be retrieved. err=-3
[2026-07-01 15:18:55 TP5] get env HCCL_BUFFSIZE = 200
[W701 15:18:55.271195945 socket.cpp:207] [c10d] The hostname of the client socket cannot be retrieved. err=-3
[2026-07-01 15:18:55 TP11] Init torch distributed begin.
[2026-07-01 15:18:55 TP15] Init torch distributed begin.
[2026-07-01 15:18:55 TP10] Init torch distributed begin.
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:362: ImportWarning: 
    *************************************************************************************************************
    The torch.Tensor.cuda and torch.nn.Module.cuda are replaced with torch.Tensor.npu and torch.nn.Module.npu now..
    The torch.cuda.DoubleTensor is replaced with torch.npu.FloatTensor cause the double type is not supported now..
    The backend in torch.distributed.init_process_group set to hccl now..
    The torch.cuda.* and torch.cuda.amp.* are replaced with torch.npu.* and torch.npu.amp.* now..
    The device parameters have been replaced with npu in the function below:
    torch.logspace, torch.randint, torch.hann_window, torch.rand, torch.full_like, torch.ones_like, torch.rand_like, torch.randperm, torch.arange, torch.frombuffer, torch.normal, torch._empty_per_channel_affine_quantized, torch.empty_strided, torch.empty_like, torch.scalar_tensor, torch.tril_indices, torch.bartlett_window, torch.ones, torch.sparse_coo_tensor, torch.randn, torch.kaiser_window, torch.tensor, torch.triu_indices, torch.as_tensor, torch.zeros, torch.randint_like, torch.full, torch.eye, torch._sparse_csr_tensor_unsafe, torch.empty, torch._sparse_coo_tensor_unsafe, torch.blackman_window, torch.zeros_like, torch.range, torch.sparse_csr_tensor, torch.randn_like, torch.from_file, torch._cudnn_init_dropout_state, torch._empty_affine_quantized, torch.linspace, torch.hamming_window, torch.empty_quantized, torch._pin_memory, torch.load, torch.set_default_device, torch.get_device_module, torch.sparse_compressed_tensor, torch.Tensor.new_empty, torch.Tensor.new_empty_strided, torch.Tensor.new_full, torch.Tensor.new_ones, torch.Tensor.new_tensor, torch.Tensor.new_zeros, torch.Tensor.to, torch.Tensor.pin_memory, torch.nn.Module.to, torch.nn.Module.to_empty
    *************************************************************************************************************
    
  warnings.warn(msg, ImportWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:291: RuntimeWarning: torch.jit.script and torch.jit.script_method will be disabled by transfer_to_npu, which currently does not support them, if you need to enable them, please do not use transfer_to_npu.
  warnings.warn(msg, RuntimeWarning)
[2026-07-01 15:18:55 TP7] get env HCCL_BUFFSIZE = 200
[W701 15:18:55.475521766 socket.cpp:207] [c10d] The hostname of the client socket cannot be retrieved. err=-3
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:362: ImportWarning: 
    *************************************************************************************************************
    The torch.Tensor.cuda and torch.nn.Module.cuda are replaced with torch.Tensor.npu and torch.nn.Module.npu now..
    The torch.cuda.DoubleTensor is replaced with torch.npu.FloatTensor cause the double type is not supported now..
    The backend in torch.distributed.init_process_group set to hccl now..
    The torch.cuda.* and torch.cuda.amp.* are replaced with torch.npu.* and torch.npu.amp.* now..
    The device parameters have been replaced with npu in the function below:
    torch.logspace, torch.randint, torch.hann_window, torch.rand, torch.full_like, torch.ones_like, torch.rand_like, torch.randperm, torch.arange, torch.frombuffer, torch.normal, torch._empty_per_channel_affine_quantized, torch.empty_strided, torch.empty_like, torch.scalar_tensor, torch.tril_indices, torch.bartlett_window, torch.ones, torch.sparse_coo_tensor, torch.randn, torch.kaiser_window, torch.tensor, torch.triu_indices, torch.as_tensor, torch.zeros, torch.randint_like, torch.full, torch.eye, torch._sparse_csr_tensor_unsafe, torch.empty, torch._sparse_coo_tensor_unsafe, torch.blackman_window, torch.zeros_like, torch.range, torch.sparse_csr_tensor, torch.randn_like, torch.from_file, torch._cudnn_init_dropout_state, torch._empty_affine_quantized, torch.linspace, torch.hamming_window, torch.empty_quantized, torch._pin_memory, torch.load, torch.set_default_device, torch.get_device_module, torch.sparse_compressed_tensor, torch.Tensor.new_empty, torch.Tensor.new_empty_strided, torch.Tensor.new_full, torch.Tensor.new_ones, torch.Tensor.new_tensor, torch.Tensor.new_zeros, torch.Tensor.to, torch.Tensor.pin_memory, torch.nn.Module.to, torch.nn.Module.to_empty
    *************************************************************************************************************
    
  warnings.warn(msg, ImportWarning)
/usr/local/python3.11.15/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py:291: RuntimeWarning: torch.jit.script and torch.jit.script_method will be disabled by transfer_to_npu, which currently does not support them, if you need to enable them, please do not use transfer_to_npu.
  warnings.warn(msg, RuntimeWarning)
[2026-07-01 15:18:56 TP13] Init torch distributed begin.
[2026-07-01 15:18:56 TP14] get env HCCL_BUFFSIZE = 200
[W701 15:18:56.812721779 socket.cpp:207] [c10d] The hostname of the client socket cannot be retrieved. err=-3
[2026-07-01 15:18:56 TP12] Init torch distributed begin.
[2026-07-01 15:18:56 TP9] get env HCCL_BUFFSIZE = 200
[2026-07-01 15:18:56 TP10] get env HCCL_BUFFSIZE = 200
[W701 15:18:56.214071826 socket.cpp:207] [c10d] The hostname of the client socket cannot be retrieved. err=-3
[2026-07-01 15:18:56 TP11] get env HCCL_BUFFSIZE = 200
[W701 15:18:56.214900164 socket.cpp:207] [c10d] The hostname of the client socket cannot be retrieved. err=-3
[W701 15:18:56.214900854 socket.cpp:207] [c10d] The hostname of the client socket cannot be retrieved. err=-3
[2026-07-01 15:18:56 TP15] get env HCCL_BUFFSIZE = 200
[W701 15:18:56.555152158 socket.cpp:207] [c10d] The hostname of the client socket cannot be retrieved. err=-3
[2026-07-01 15:18:57 TP12] get env HCCL_BUFFSIZE = 200
[W701 15:18:57.829326609 socket.cpp:207] [c10d] The hostname of the client socket cannot be retrieved. err=-3
[2026-07-01 15:18:57 TP13] get env HCCL_BUFFSIZE = 200
[W701 15:18:57.839549652 socket.cpp:207] [c10d] The hostname of the client socket cannot be retrieved. err=-3
[Gloo] Rank 0 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 7 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 1 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 2 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 4 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 8 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 9 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 6 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 3 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 5 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 13 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 15 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 10 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 11 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 12 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 14 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 0 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 9 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 1 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 12 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 2 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 3 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 4 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 5 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 6 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 7 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 8 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 10 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 14 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 11 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 13 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[Gloo] Rank 15 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
[2026-07-01 15:18:57 TP0] DCP disabled, dcp_size=1, tp_size=16
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
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
[2026-07-01 15:18:57 TP0] Init torch distributed ends. elapsed=3.90 s, mem usage=0.01 GB
[2026-07-01 15:18:57 TP14] Init torch distributed ends. elapsed=2.60 s, mem usage=0.01 GB
[2026-07-01 15:18:57 TP15] Init torch distributed ends. elapsed=2.21 s, mem usage=0.01 GB
[2026-07-01 15:18:57 TP12] Init torch distributed ends. elapsed=1.57 s, mem usage=0.01 GB
[2026-07-01 15:18:57 TP11] Init torch distributed ends. elapsed=2.23 s, mem usage=0.01 GB
[2026-07-01 15:18:57 TP13] Init torch distributed ends. elapsed=1.75 s, mem usage=0.01 GB
[2026-07-01 15:18:57 TP10] Init torch distributed ends. elapsed=2.20 s, mem usage=0.01 GB
[2026-07-01 15:18:57 TP9] Init torch distributed ends. elapsed=2.32 s, mem usage=0.01 GB
[2026-07-01 15:18:57 TP5] Init torch distributed ends. elapsed=3.13 s, mem usage=0.01 GB
[2026-07-01 15:18:57 TP8] Init torch distributed ends. elapsed=3.18 s, mem usage=0.01 GB
[2026-07-01 15:18:57 TP6] Init torch distributed ends. elapsed=3.34 s, mem usage=0.01 GB
[2026-07-01 15:18:57 TP4] Init torch distributed ends. elapsed=4.18 s, mem usage=0.01 GB
[2026-07-01 15:18:57 TP2] Init torch distributed ends. elapsed=3.33 s, mem usage=0.01 GB
[2026-07-01 15:18:57 TP1] Init torch distributed ends. elapsed=4.34 s, mem usage=0.01 GB
[2026-07-01 15:18:57 TP3] Init torch distributed ends. elapsed=3.64 s, mem usage=0.01 GB
[2026-07-01 15:18:57 TP7] Init torch distributed ends. elapsed=2.91 s, mem usage=0.01 GB
[2026-07-01 15:18:58 TP4] Ignore import error when loading sglang.srt.models.bailing_moe_linear: No module named 'vllm'
[2026-07-01 15:18:58 TP0] Ignore import error when loading sglang.srt.models.bailing_moe_linear: No module named 'vllm'
[2026-07-01 15:18:58 TP12] Ignore import error when loading sglang.srt.models.bailing_moe_linear: No module named 'vllm'
[2026-07-01 15:18:58 TP2] Ignore import error when loading sglang.srt.models.bailing_moe_linear: No module named 'vllm'
[2026-07-01 15:18:58 TP5] Ignore import error when loading sglang.srt.models.bailing_moe_linear: No module named 'vllm'
[2026-07-01 15:18:58 TP10] Ignore import error when loading sglang.srt.models.bailing_moe_linear: No module named 'vllm'
[2026-07-01 15:18:58 TP8] Ignore import error when loading sglang.srt.models.bailing_moe_linear: No module named 'vllm'
[2026-07-01 15:18:58 TP6] Ignore import error when loading sglang.srt.models.bailing_moe_linear: No module named 'vllm'
[2026-07-01 15:18:58 TP9] Ignore import error when loading sglang.srt.models.bailing_moe_linear: No module named 'vllm'
[2026-07-01 15:18:58 TP13] Ignore import error when loading sglang.srt.models.bailing_moe_linear: No module named 'vllm'
[2026-07-01 15:18:58 TP7] Ignore import error when loading sglang.srt.models.bailing_moe_linear: No module named 'vllm'
[2026-07-01 15:18:58 TP14] Ignore import error when loading sglang.srt.models.bailing_moe_linear: No module named 'vllm'
[2026-07-01 15:18:58 TP3] Ignore import error when loading sglang.srt.models.bailing_moe_linear: No module named 'vllm'
[2026-07-01 15:18:58 TP1] Ignore import error when loading sglang.srt.models.bailing_moe_linear: No module named 'vllm'
[2026-07-01 15:18:58 TP11] Ignore import error when loading sglang.srt.models.bailing_moe_linear: No module named 'vllm'
[2026-07-01 15:18:58 TP15] Ignore import error when loading sglang.srt.models.bailing_moe_linear: No module named 'vllm'
[2026-07-01 15:18:58 TP4] Ignore import error when loading sglang.srt.models.bailing_moe_nextn: No module named 'vllm'
[2026-07-01 15:18:58 TP0] Ignore import error when loading sglang.srt.models.bailing_moe_nextn: No module named 'vllm'
[2026-07-01 15:18:58 TP2] Ignore import error when loading sglang.srt.models.bailing_moe_nextn: No module named 'vllm'
[2026-07-01 15:18:58 TP5] Ignore import error when loading sglang.srt.models.bailing_moe_nextn: No module named 'vllm'
[2026-07-01 15:18:58 TP12] Ignore import error when loading sglang.srt.models.bailing_moe_nextn: No module named 'vllm'
[2026-07-01 15:18:58 TP10] Ignore import error when loading sglang.srt.models.bailing_moe_nextn: No module named 'vllm'
[2026-07-01 15:18:58 TP8] Ignore import error when loading sglang.srt.models.bailing_moe_nextn: No module named 'vllm'
[2026-07-01 15:18:58 TP6] Ignore import error when loading sglang.srt.models.bailing_moe_nextn: No module named 'vllm'
[2026-07-01 15:18:58 TP9] Ignore import error when loading sglang.srt.models.bailing_moe_nextn: No module named 'vllm'
[2026-07-01 15:18:58 TP7] Ignore import error when loading sglang.srt.models.bailing_moe_nextn: No module named 'vllm'
[2026-07-01 15:18:58 TP3] Ignore import error when loading sglang.srt.models.bailing_moe_nextn: No module named 'vllm'
[2026-07-01 15:18:58 TP15] Ignore import error when loading sglang.srt.models.bailing_moe_nextn: No module named 'vllm'
[2026-07-01 15:18:58 TP13] Ignore import error when loading sglang.srt.models.bailing_moe_nextn: No module named 'vllm'
[2026-07-01 15:18:58 TP14] Ignore import error when loading sglang.srt.models.bailing_moe_nextn: No module named 'vllm'
[2026-07-01 15:18:58 TP11] Ignore import error when loading sglang.srt.models.bailing_moe_nextn: No module named 'vllm'
[2026-07-01 15:18:58 TP1] Ignore import error when loading sglang.srt.models.bailing_moe_nextn: No module named 'vllm'
[2026-07-01 15:18:58 TP13] tilelang not installed; deepseek_v4_rope pass_configs unset. Triton kernels in this module still run; only downstream tilelang.jit consumers of pass_configs will need to handle the None.
[2026-07-01 15:18:58 TP3] tilelang not installed; deepseek_v4_rope pass_configs unset. Triton kernels in this module still run; only downstream tilelang.jit consumers of pass_configs will need to handle the None.
[2026-07-01 15:18:58 TP6] tilelang not installed; deepseek_v4_rope pass_configs unset. Triton kernels in this module still run; only downstream tilelang.jit consumers of pass_configs will need to handle the None.
[2026-07-01 15:18:58 TP4] tilelang not installed; deepseek_v4_rope pass_configs unset. Triton kernels in this module still run; only downstream tilelang.jit consumers of pass_configs will need to handle the None.
[2026-07-01 15:18:58 TP10] tilelang not installed; deepseek_v4_rope pass_configs unset. Triton kernels in this module still run; only downstream tilelang.jit consumers of pass_configs will need to handle the None.
[2026-07-01 15:18:58 TP0] tilelang not installed; deepseek_v4_rope pass_configs unset. Triton kernels in this module still run; only downstream tilelang.jit consumers of pass_configs will need to handle the None.
[2026-07-01 15:18:58 TP12] tilelang not installed; deepseek_v4_rope pass_configs unset. Triton kernels in this module still run; only downstream tilelang.jit consumers of pass_configs will need to handle the None.
[2026-07-01 15:18:58 TP15] tilelang not installed; deepseek_v4_rope pass_configs unset. Triton kernels in this module still run; only downstream tilelang.jit consumers of pass_configs will need to handle the None.
[2026-07-01 15:18:58 TP5] tilelang not installed; deepseek_v4_rope pass_configs unset. Triton kernels in this module still run; only downstream tilelang.jit consumers of pass_configs will need to handle the None.
[2026-07-01 15:18:58 TP2] tilelang not installed; deepseek_v4_rope pass_configs unset. Triton kernels in this module still run; only downstream tilelang.jit consumers of pass_configs will need to handle the None.
[2026-07-01 15:18:58 TP9] tilelang not installed; deepseek_v4_rope pass_configs unset. Triton kernels in this module still run; only downstream tilelang.jit consumers of pass_configs will need to handle the None.
[2026-07-01 15:18:58 TP8] tilelang not installed; deepseek_v4_rope pass_configs unset. Triton kernels in this module still run; only downstream tilelang.jit consumers of pass_configs will need to handle the None.
[2026-07-01 15:18:58 TP7] tilelang not installed; deepseek_v4_rope pass_configs unset. Triton kernels in this module still run; only downstream tilelang.jit consumers of pass_configs will need to handle the None.
[2026-07-01 15:18:58 TP11] tilelang not installed; deepseek_v4_rope pass_configs unset. Triton kernels in this module still run; only downstream tilelang.jit consumers of pass_configs will need to handle the None.
[2026-07-01 15:18:58 TP1] tilelang not installed; deepseek_v4_rope pass_configs unset. Triton kernels in this module still run; only downstream tilelang.jit consumers of pass_configs will need to handle the None.
[2026-07-01 15:18:58 TP14] tilelang not installed; deepseek_v4_rope pass_configs unset. Triton kernels in this module still run; only downstream tilelang.jit consumers of pass_configs will need to handle the None.
[2026-07-01 15:18:58 TP5] Ignore import error when loading sglang.srt.models.mindspore: No module named 'mindspore'
[2026-07-01 15:18:58 TP4] Ignore import error when loading sglang.srt.models.mindspore: No module named 'mindspore'
[2026-07-01 15:18:58 TP8] Ignore import error when loading sglang.srt.models.mindspore: No module named 'mindspore'
[2026-07-01 15:18:58 TP0] Ignore import error when loading sglang.srt.models.mindspore: No module named 'mindspore'
[2026-07-01 15:18:58 TP3] Ignore import error when loading sglang.srt.models.mindspore: No module named 'mindspore'
[2026-07-01 15:18:58 TP9] Ignore import error when loading sglang.srt.models.mindspore: No module named 'mindspore'
[2026-07-01 15:18:58 TP12] Ignore import error when loading sglang.srt.models.mindspore: No module named 'mindspore'
[2026-07-01 15:18:58 TP6] Ignore import error when loading sglang.srt.models.mindspore: No module named 'mindspore'
[2026-07-01 15:18:58 TP2] Ignore import error when loading sglang.srt.models.mindspore: No module named 'mindspore'
[2026-07-01 15:18:58 TP14] Ignore import error when loading sglang.srt.models.mindspore: No module named 'mindspore'
[2026-07-01 15:18:58 TP13] Ignore import error when loading sglang.srt.models.mindspore: No module named 'mindspore'
[2026-07-01 15:18:58 TP10] Ignore import error when loading sglang.srt.models.mindspore: No module named 'mindspore'
[2026-07-01 15:18:58 TP1] Ignore import error when loading sglang.srt.models.mindspore: No module named 'mindspore'
[2026-07-01 15:18:58 TP11] Ignore import error when loading sglang.srt.models.mindspore: No module named 'mindspore'
[2026-07-01 15:18:58 TP7] Ignore import error when loading sglang.srt.models.mindspore: No module named 'mindspore'
[2026-07-01 15:18:58 TP15] Ignore import error when loading sglang.srt.models.mindspore: No module named 'mindspore'
[2026-07-01 15:18:59 TP9] Load weight begin. avail mem=61.12 GB
[2026-07-01 15:18:59 TP2] Load weight begin. avail mem=60.88 GB
[2026-07-01 15:18:59 TP10] Load weight begin. avail mem=60.88 GB
[2026-07-01 15:18:59 TP13] Load weight begin. avail mem=61.11 GB
[2026-07-01 15:18:59 TP6] Load weight begin. avail mem=60.88 GB
[2026-07-01 15:18:59 TP14] Load weight begin. avail mem=60.82 GB
[2026-07-01 15:18:59 TP5] Load weight begin. avail mem=61.11 GB
[2026-07-01 15:18:59 TP8] Load weight begin. avail mem=60.87 GB
[2026-07-01 15:18:59 TP15] Load weight begin. avail mem=61.12 GB
[2026-07-01 15:18:59 TP12] Load weight begin. avail mem=60.88 GB
[2026-07-01 15:18:59 TP11] Load weight begin. avail mem=61.11 GB
[2026-07-01 15:18:59 TP4] Load weight begin. avail mem=60.88 GB
[2026-07-01 15:18:59 TP3] Load weight begin. avail mem=61.11 GB
[2026-07-01 15:18:59 TP1] Load weight begin. avail mem=61.11 GB
[2026-07-01 15:18:59 TP7] Load weight begin. avail mem=61.11 GB
[2026-07-01 15:18:59 TP0] Load weight begin. avail mem=60.81 GB
[2026-07-01 15:18:59 TP10] FlashInfer TRTLLM MoE deferred finalize is disabled (moe_runner_backend=auto, quant_method=UnquantizedFusedMoEMethod).
[2026-07-01 15:18:59 TP3] FlashInfer TRTLLM MoE deferred finalize is disabled (moe_runner_backend=auto, quant_method=UnquantizedFusedMoEMethod).
[2026-07-01 15:18:59 TP13] FlashInfer TRTLLM MoE deferred finalize is disabled (moe_runner_backend=auto, quant_method=UnquantizedFusedMoEMethod).
[2026-07-01 15:18:59 TP9] FlashInfer TRTLLM MoE deferred finalize is disabled (moe_runner_backend=auto, quant_method=UnquantizedFusedMoEMethod).
[2026-07-01 15:18:59 TP15] FlashInfer TRTLLM MoE deferred finalize is disabled (moe_runner_backend=auto, quant_method=UnquantizedFusedMoEMethod).
[2026-07-01 15:18:59 TP5] FlashInfer TRTLLM MoE deferred finalize is disabled (moe_runner_backend=auto, quant_method=UnquantizedFusedMoEMethod).
[2026-07-01 15:18:59 TP2] FlashInfer TRTLLM MoE deferred finalize is disabled (moe_runner_backend=auto, quant_method=UnquantizedFusedMoEMethod).
[2026-07-01 15:18:59 TP6] FlashInfer TRTLLM MoE deferred finalize is disabled (moe_runner_backend=auto, quant_method=UnquantizedFusedMoEMethod).
[2026-07-01 15:18:59 TP1] FlashInfer TRTLLM MoE deferred finalize is disabled (moe_runner_backend=auto, quant_method=UnquantizedFusedMoEMethod).
[2026-07-01 15:18:59 TP8] FlashInfer TRTLLM MoE deferred finalize is disabled (moe_runner_backend=auto, quant_method=UnquantizedFusedMoEMethod).
[2026-07-01 15:18:59 TP12] FlashInfer TRTLLM MoE deferred finalize is disabled (moe_runner_backend=auto, quant_method=UnquantizedFusedMoEMethod).
[2026-07-01 15:18:59 TP11] FlashInfer TRTLLM MoE deferred finalize is disabled (moe_runner_backend=auto, quant_method=UnquantizedFusedMoEMethod).
[2026-07-01 15:18:59 TP7] FlashInfer TRTLLM MoE deferred finalize is disabled (moe_runner_backend=auto, quant_method=UnquantizedFusedMoEMethod).
[2026-07-01 15:18:59 TP0] FlashInfer TRTLLM MoE deferred finalize is disabled (moe_runner_backend=auto, quant_method=UnquantizedFusedMoEMethod).
[2026-07-01 15:18:59 TP4] FlashInfer TRTLLM MoE deferred finalize is disabled (moe_runner_backend=auto, quant_method=UnquantizedFusedMoEMethod).
[2026-07-01 15:18:59 TP14] FlashInfer TRTLLM MoE deferred finalize is disabled (moe_runner_backend=auto, quant_method=UnquantizedFusedMoEMethod).
Multi-thread loading shards:  97% Completed | 62/64 [00:27<00:00,  2.35it/s][2026-07-01 15:19:30 TP11] #all_names: 707, #hit_names: 707, #missing_exclude_scales: 0
Multi-thread loading shards:  98% Completed | 63/64 [00:27<00:00,  2.34it/s][2026-07-01 15:19:30 TP5] #all_names: 707, #hit_names: 707, #missing_exclude_scales: 0
[2026-07-01 15:19:30 TP3] #all_names: 707, #hit_names: 707, #missing_exclude_scales: 0
[2026-07-01 15:19:31 TP7] #all_names: 707, #hit_names: 707, #missing_exclude_scales: 0
[2026-07-01 15:19:31 TP10] #all_names: 707, #hit_names: 707, #missing_exclude_scales: 0
[2026-07-01 15:19:32 TP4] #all_names: 707, #hit_names: 707, #missing_exclude_scales: 0
Multi-thread loading shards: 100% Completed | 64/64 [00:29<00:00,  2.18it/s]
[2026-07-01 15:19:32 TP0] #all_names: 707, #hit_names: 707, #missing_exclude_scales: 0
[2026-07-01 15:19:32 TP11] get env ASCEND_OPP_PATH = /usr/local/Ascend/cann-9.0.0/opp
[2026-07-01 15:19:32 TP5] get env ASCEND_OPP_PATH = /usr/local/Ascend/cann-9.0.0/opp
[2026-07-01 15:19:32 TP3] get env ASCEND_OPP_PATH = /usr/local/Ascend/cann-9.0.0/opp
[2026-07-01 15:19:32 TP6] #all_names: 707, #hit_names: 707, #missing_exclude_scales: 0
[2026-07-01 15:19:32 TP1] #all_names: 707, #hit_names: 707, #missing_exclude_scales: 0
[2026-07-01 15:19:33 TP14] #all_names: 707, #hit_names: 707, #missing_exclude_scales: 0
[2026-07-01 15:19:33 TP9] #all_names: 707, #hit_names: 707, #missing_exclude_scales: 0
[2026-07-01 15:19:33 TP15] #all_names: 707, #hit_names: 707, #missing_exclude_scales: 0
[2026-07-01 15:19:33 TP8] #all_names: 707, #hit_names: 707, #missing_exclude_scales: 0
[2026-07-01 15:19:33 TP13] #all_names: 707, #hit_names: 707, #missing_exclude_scales: 0
[2026-07-01 15:19:33 TP4] get env ASCEND_OPP_PATH = /usr/local/Ascend/cann-9.0.0/opp
[2026-07-01 15:19:33 TP10] get env ASCEND_OPP_PATH = /usr/local/Ascend/cann-9.0.0/opp
[2026-07-01 15:19:33 TP7] get env ASCEND_OPP_PATH = /usr/local/Ascend/cann-9.0.0/opp
[2026-07-01 15:19:33 TP0] get env ASCEND_OPP_PATH = /usr/local/Ascend/cann-9.0.0/opp
[2026-07-01 15:19:34 TP6] get env ASCEND_OPP_PATH = /usr/local/Ascend/cann-9.0.0/opp
[2026-07-01 15:19:34 TP9] get env ASCEND_OPP_PATH = /usr/local/Ascend/cann-9.0.0/opp
[2026-07-01 15:19:34 TP1] get env ASCEND_OPP_PATH = /usr/local/Ascend/cann-9.0.0/opp
[2026-07-01 15:19:34 TP14] get env ASCEND_OPP_PATH = /usr/local/Ascend/cann-9.0.0/opp
[2026-07-01 15:19:34 TP15] get env ASCEND_OPP_PATH = /usr/local/Ascend/cann-9.0.0/opp
[2026-07-01 15:19:34 TP8] get env ASCEND_OPP_PATH = /usr/local/Ascend/cann-9.0.0/opp
[2026-07-01 15:19:34 TP12] #all_names: 707, #hit_names: 707, #missing_exclude_scales: 0
[2026-07-01 15:19:35 TP2] #all_names: 707, #hit_names: 707, #missing_exclude_scales: 0
[2026-07-01 15:19:35 TP13] get env ASCEND_OPP_PATH = /usr/local/Ascend/cann-9.0.0/opp
[2026-07-01 15:19:36 TP12] get env ASCEND_OPP_PATH = /usr/local/Ascend/cann-9.0.0/opp
[2026-07-01 15:19:36 TP2] get env ASCEND_OPP_PATH = /usr/local/Ascend/cann-9.0.0/opp
[2026-07-01 15:19:42 TP11] get env HOME = /root
[2026-07-01 15:19:42 TP11] get env TE_AUTO_RESTART_COUNTER = 0
[2026-07-01 15:19:43 TP5] get env HOME = /root
[2026-07-01 15:19:43 TP11] get env PYTHONPATH = /data/wzy/sgl-sglang/python:/usr/local/Ascend/cann-9.0.0/python/site-packages:/usr/local/Ascend/cann-9.0.0/opp/built-in/op_impl/ai_core/tbe:/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe:
[2026-07-01 15:19:43 TP5] get env TE_AUTO_RESTART_COUNTER = 0
[2026-07-01 15:19:43 TP3] get env HOME = /root
[2026-07-01 15:19:43 TP4] get env HOME = /root
[2026-07-01 15:19:43 TP3] get env TE_AUTO_RESTART_COUNTER = 0
[2026-07-01 15:19:43 TP4] get env TE_AUTO_RESTART_COUNTER = 0
[2026-07-01 15:19:43 TP10] get env HOME = /root
[2026-07-01 15:19:43 TP11] Load weight end. elapsed=44.81 s, type=Grok1ForCausalLM, avail mem=25.54 GB, mem usage=35.57 GB.
[2026-07-01 15:19:44 TP10] get env TE_AUTO_RESTART_COUNTER = 0
[2026-07-01 15:19:44 TP7] get env HOME = /root
[2026-07-01 15:19:44 TP7] get env TE_AUTO_RESTART_COUNTER = 0
[2026-07-01 15:19:44 TP5] get env PYTHONPATH = /data/wzy/sgl-sglang/python:/usr/local/Ascend/cann-9.0.0/python/site-packages:/usr/local/Ascend/cann-9.0.0/opp/built-in/op_impl/ai_core/tbe:/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe:
[2026-07-01 15:19:44 TP0] get env HOME = /root
[2026-07-01 15:19:45 TP0] get env TE_AUTO_RESTART_COUNTER = 0
[2026-07-01 15:19:45 TP4] get env PYTHONPATH = /data/wzy/sgl-sglang/python:/usr/local/Ascend/cann-9.0.0/python/site-packages:/usr/local/Ascend/cann-9.0.0/opp/built-in/op_impl/ai_core/tbe:/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe:
[2026-07-01 15:19:45 TP3] get env PYTHONPATH = /data/wzy/sgl-sglang/python:/usr/local/Ascend/cann-9.0.0/python/site-packages:/usr/local/Ascend/cann-9.0.0/opp/built-in/op_impl/ai_core/tbe:/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe:
[2026-07-01 15:19:45 TP10] get env PYTHONPATH = /data/wzy/sgl-sglang/python:/usr/local/Ascend/cann-9.0.0/python/site-packages:/usr/local/Ascend/cann-9.0.0/opp/built-in/op_impl/ai_core/tbe:/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe:
[2026-07-01 15:19:45 TP7] get env PYTHONPATH = /data/wzy/sgl-sglang/python:/usr/local/Ascend/cann-9.0.0/python/site-packages:/usr/local/Ascend/cann-9.0.0/opp/built-in/op_impl/ai_core/tbe:/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe:
[2026-07-01 15:19:45 TP6] get env HOME = /root
[2026-07-01 15:19:45 TP5] Load weight end. elapsed=46.65 s, type=Grok1ForCausalLM, avail mem=25.54 GB, mem usage=35.57 GB.
[2026-07-01 15:19:46 TP6] get env TE_AUTO_RESTART_COUNTER = 0
[2026-07-01 15:19:46 TP3] Load weight end. elapsed=47.02 s, type=Grok1ForCausalLM, avail mem=25.54 GB, mem usage=35.57 GB.
[2026-07-01 15:19:46 TP4] Load weight end. elapsed=47.09 s, type=Grok1ForCausalLM, avail mem=25.31 GB, mem usage=35.57 GB.
[2026-07-01 15:19:46 TP0] get env PYTHONPATH = /data/wzy/sgl-sglang/python:/usr/local/Ascend/cann-9.0.0/python/site-packages:/usr/local/Ascend/cann-9.0.0/opp/built-in/op_impl/ai_core/tbe:/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe:
[2026-07-01 15:19:46 TP10] Load weight end. elapsed=47.45 s, type=Grok1ForCausalLM, avail mem=25.31 GB, mem usage=35.57 GB.
[2026-07-01 15:19:46 TP7] Load weight end. elapsed=47.55 s, type=Grok1ForCausalLM, avail mem=25.54 GB, mem usage=35.57 GB.
[2026-07-01 15:19:46 TP9] get env HOME = /root
[2026-07-01 15:19:47 TP9] get env TE_AUTO_RESTART_COUNTER = 0
[2026-07-01 15:19:47 TP6] get env PYTHONPATH = /data/wzy/sgl-sglang/python:/usr/local/Ascend/cann-9.0.0/python/site-packages:/usr/local/Ascend/cann-9.0.0/opp/built-in/op_impl/ai_core/tbe:/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe:
[2026-07-01 15:19:47 TP1] get env HOME = /root
[2026-07-01 15:19:47 TP8] get env HOME = /root
[2026-07-01 15:19:47 TP1] get env TE_AUTO_RESTART_COUNTER = 0
[2026-07-01 15:19:47 TP0] Load weight end. elapsed=48.44 s, type=Grok1ForCausalLM, avail mem=25.24 GB, mem usage=35.57 GB.
[2026-07-01 15:19:47 TP14] get env HOME = /root
[2026-07-01 15:19:47 TP8] get env TE_AUTO_RESTART_COUNTER = 0
[2026-07-01 15:19:47 TP15] get env HOME = /root
[2026-07-01 15:19:47 TP14] get env TE_AUTO_RESTART_COUNTER = 0
[2026-07-01 15:19:47 TP15] get env TE_AUTO_RESTART_COUNTER = 0
[2026-07-01 15:19:48 TP13] get env HOME = /root
[2026-07-01 15:19:48 TP9] get env PYTHONPATH = /data/wzy/sgl-sglang/python:/usr/local/Ascend/cann-9.0.0/python/site-packages:/usr/local/Ascend/cann-9.0.0/opp/built-in/op_impl/ai_core/tbe:/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe:
[2026-07-01 15:19:48 TP6] Load weight end. elapsed=49.07 s, type=Grok1ForCausalLM, avail mem=25.31 GB, mem usage=35.57 GB.
[2026-07-01 15:19:48 TP13] get env TE_AUTO_RESTART_COUNTER = 0
[2026-07-01 15:19:48 TP1] get env PYTHONPATH = /data/wzy/sgl-sglang/python:/usr/local/Ascend/cann-9.0.0/python/site-packages:/usr/local/Ascend/cann-9.0.0/opp/built-in/op_impl/ai_core/tbe:/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe:
[2026-07-01 15:19:48 TP8] get env PYTHONPATH = /data/wzy/sgl-sglang/python:/usr/local/Ascend/cann-9.0.0/python/site-packages:/usr/local/Ascend/cann-9.0.0/opp/built-in/op_impl/ai_core/tbe:/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe:
[2026-07-01 15:19:49 TP14] get env PYTHONPATH = /data/wzy/sgl-sglang/python:/usr/local/Ascend/cann-9.0.0/python/site-packages:/usr/local/Ascend/cann-9.0.0/opp/built-in/op_impl/ai_core/tbe:/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe:
[2026-07-01 15:19:49 TP15] get env PYTHONPATH = /data/wzy/sgl-sglang/python:/usr/local/Ascend/cann-9.0.0/python/site-packages:/usr/local/Ascend/cann-9.0.0/opp/built-in/op_impl/ai_core/tbe:/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe:
[2026-07-01 15:19:49 TP9] Load weight end. elapsed=50.37 s, type=Grok1ForCausalLM, avail mem=25.55 GB, mem usage=35.57 GB.
[2026-07-01 15:19:49 TP13] get env PYTHONPATH = /data/wzy/sgl-sglang/python:/usr/local/Ascend/cann-9.0.0/python/site-packages:/usr/local/Ascend/cann-9.0.0/opp/built-in/op_impl/ai_core/tbe:/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe:
[2026-07-01 15:19:49 TP8] Load weight end. elapsed=50.80 s, type=Grok1ForCausalLM, avail mem=25.30 GB, mem usage=35.57 GB.
[2026-07-01 15:19:50 TP1] Load weight end. elapsed=50.89 s, type=Grok1ForCausalLM, avail mem=25.54 GB, mem usage=35.57 GB.
[2026-07-01 15:19:50 TP12] get env HOME = /root
[2026-07-01 15:19:50 TP14] Load weight end. elapsed=51.21 s, type=Grok1ForCausalLM, avail mem=25.31 GB, mem usage=35.51 GB.
[2026-07-01 15:19:50 TP2] get env HOME = /root
[2026-07-01 15:19:50 TP12] get env TE_AUTO_RESTART_COUNTER = 0
[2026-07-01 15:19:50 TP15] Load weight end. elapsed=51.36 s, type=Grok1ForCausalLM, avail mem=25.55 GB, mem usage=35.57 GB.
[2026-07-01 15:19:50 TP2] get env TE_AUTO_RESTART_COUNTER = 0
[2026-07-01 15:19:50 TP13] Load weight end. elapsed=51.43 s, type=Grok1ForCausalLM, avail mem=25.54 GB, mem usage=35.57 GB.
[2026-07-01 15:19:51 TP12] get env PYTHONPATH = /data/wzy/sgl-sglang/python:/usr/local/Ascend/cann-9.0.0/python/site-packages:/usr/local/Ascend/cann-9.0.0/opp/built-in/op_impl/ai_core/tbe:/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe:
[2026-07-01 15:19:51 TP2] get env PYTHONPATH = /data/wzy/sgl-sglang/python:/usr/local/Ascend/cann-9.0.0/python/site-packages:/usr/local/Ascend/cann-9.0.0/opp/built-in/op_impl/ai_core/tbe:/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe:
[2026-07-01 15:19:52 TP12] Load weight end. elapsed=52.96 s, type=Grok1ForCausalLM, avail mem=25.31 GB, mem usage=35.57 GB.
[2026-07-01 15:19:52 TP2] Load weight end. elapsed=53.02 s, type=Grok1ForCausalLM, avail mem=25.31 GB, mem usage=35.57 GB.
/data/wzy/sgl-sglang/python/sglang/srt/utils/common.py:1466: UserWarning: The given NumPy array is not writable, and PyTorch does not support non-writable tensors. This means writing to this tensor will result in undefined behavior. You may want to copy the array to protect its data or make it writable before converting it to a tensor. This type of warning will be suppressed for the rest of this program. (Triggered internally at /pytorch/torch/csrc/utils/tensor_numpy.cpp:213.)
  tensor_data = torch.ByteTensor(
[2026-07-01 15:19:55 TP0] KV Cache is allocated. dtype: torch.bfloat16, #tokens: 387968, K size: 5.92 GB, V size: 5.92 GB
[2026-07-01 15:19:55 TP0] Memory pool end. avail mem=11.15 GB
[2026-07-01 15:19:55 TP9] KV Cache is allocated. dtype: torch.bfloat16, #tokens: 387968, K size: 5.92 GB, V size: 5.92 GB
[2026-07-01 15:19:55 TP9] Memory pool end. avail mem=11.47 GB
[2026-07-01 15:19:55 TP2] KV Cache is allocated. dtype: torch.bfloat16, #tokens: 387968, K size: 5.92 GB, V size: 5.92 GB
[2026-07-01 15:19:55 TP2] Memory pool end. avail mem=11.22 GB
[2026-07-01 15:19:55 TP12] KV Cache is allocated. dtype: torch.bfloat16, #tokens: 387968, K size: 5.92 GB, V size: 5.92 GB
[2026-07-01 15:19:55 TP12] Memory pool end. avail mem=11.23 GB
[2026-07-01 15:19:55 TP7] KV Cache is allocated. dtype: torch.bfloat16, #tokens: 387968, K size: 5.92 GB, V size: 5.92 GB
[2026-07-01 15:19:55 TP7] Memory pool end. avail mem=11.46 GB
[2026-07-01 15:19:55 TP2] Disable prefill CUDA graph because cuda_graph_config resolved prefill.backend='disabled' (e.g. via --cuda-graph-backend-prefill=disabled or auto-disable rules).
[2026-07-01 15:19:55 TP9] Disable prefill CUDA graph because cuda_graph_config resolved prefill.backend='disabled' (e.g. via --cuda-graph-backend-prefill=disabled or auto-disable rules).
[2026-07-01 15:19:55 TP12] Disable prefill CUDA graph because cuda_graph_config resolved prefill.backend='disabled' (e.g. via --cuda-graph-backend-prefill=disabled or auto-disable rules).
[2026-07-01 15:19:55 TP15] KV Cache is allocated. dtype: torch.bfloat16, #tokens: 387968, K size: 5.92 GB, V size: 5.92 GB
[2026-07-01 15:19:55 TP7] Disable prefill CUDA graph because cuda_graph_config resolved prefill.backend='disabled' (e.g. via --cuda-graph-backend-prefill=disabled or auto-disable rules).
[2026-07-01 15:19:55 TP15] Memory pool end. avail mem=11.47 GB
[2026-07-01 15:19:55 TP9] Tree cache initialized: source=default impl=ChunkCache hybrid_swa=False hybrid_ssm=False hierarchical=False streaming_wrapped=False
[2026-07-01 15:19:55 TP2] Tree cache initialized: source=default impl=ChunkCache hybrid_swa=False hybrid_ssm=False hierarchical=False streaming_wrapped=False
[2026-07-01 15:19:55 TP12] Tree cache initialized: source=default impl=ChunkCache hybrid_swa=False hybrid_ssm=False hierarchical=False streaming_wrapped=False
[2026-07-01 15:19:55 TP7] Tree cache initialized: source=default impl=ChunkCache hybrid_swa=False hybrid_ssm=False hierarchical=False streaming_wrapped=False
[2026-07-01 15:19:55 TP5] KV Cache is allocated. dtype: torch.bfloat16, #tokens: 387968, K size: 5.92 GB, V size: 5.92 GB
[2026-07-01 15:19:55 TP15] Disable prefill CUDA graph because cuda_graph_config resolved prefill.backend='disabled' (e.g. via --cuda-graph-backend-prefill=disabled or auto-disable rules).
[2026-07-01 15:19:55 TP5] Memory pool end. avail mem=11.46 GB
[2026-07-01 15:19:55 TP0] Disable prefill CUDA graph because cuda_graph_config resolved prefill.backend='disabled' (e.g. via --cuda-graph-backend-prefill=disabled or auto-disable rules).
[2026-07-01 15:19:55 TP0] max_total_num_tokens=387968, chunked_prefill_size=8192, max_prefill_tokens=16384, max_running_requests=2048, context_len=131072, available_gpu_mem=11.15 GB
[2026-07-01 15:19:55 TP0] Tree cache initialized: source=default impl=ChunkCache hybrid_swa=False hybrid_ssm=False hierarchical=False streaming_wrapped=False
[2026-07-01 15:19:55 TP15] Tree cache initialized: source=default impl=ChunkCache hybrid_swa=False hybrid_ssm=False hierarchical=False streaming_wrapped=False
[2026-07-01 15:19:55 TP5] Disable prefill CUDA graph because cuda_graph_config resolved prefill.backend='disabled' (e.g. via --cuda-graph-backend-prefill=disabled or auto-disable rules).
[2026-07-01 15:19:55 TP5] Tree cache initialized: source=default impl=ChunkCache hybrid_swa=False hybrid_ssm=False hierarchical=False streaming_wrapped=False
[2026-07-01 15:19:55 TP10] KV Cache is allocated. dtype: torch.bfloat16, #tokens: 387968, K size: 5.92 GB, V size: 5.92 GB
[2026-07-01 15:19:55 TP10] Memory pool end. avail mem=11.23 GB
[2026-07-01 15:19:55 TP14] KV Cache is allocated. dtype: torch.bfloat16, #tokens: 387968, K size: 5.92 GB, V size: 5.92 GB
[2026-07-01 15:19:55 TP14] Memory pool end. avail mem=11.23 GB
[2026-07-01 15:19:55 TP10] Disable prefill CUDA graph because cuda_graph_config resolved prefill.backend='disabled' (e.g. via --cuda-graph-backend-prefill=disabled or auto-disable rules).
[2026-07-01 15:19:55 TP13] KV Cache is allocated. dtype: torch.bfloat16, #tokens: 387968, K size: 5.92 GB, V size: 5.92 GB
[2026-07-01 15:19:55 TP4] KV Cache is allocated. dtype: torch.bfloat16, #tokens: 387968, K size: 5.92 GB, V size: 5.92 GB
[2026-07-01 15:19:55 TP14] Disable prefill CUDA graph because cuda_graph_config resolved prefill.backend='disabled' (e.g. via --cuda-graph-backend-prefill=disabled or auto-disable rules).
[2026-07-01 15:19:55 TP3] KV Cache is allocated. dtype: torch.bfloat16, #tokens: 387968, K size: 5.92 GB, V size: 5.92 GB
[2026-07-01 15:19:55 TP4] Memory pool end. avail mem=11.23 GB
[2026-07-01 15:19:55 TP13] Memory pool end. avail mem=11.46 GB
[2026-07-01 15:19:55 TP14] Tree cache initialized: source=default impl=ChunkCache hybrid_swa=False hybrid_ssm=False hierarchical=False streaming_wrapped=False
[2026-07-01 15:19:55 TP10] Tree cache initialized: source=default impl=ChunkCache hybrid_swa=False hybrid_ssm=False hierarchical=False streaming_wrapped=False
[2026-07-01 15:19:55 TP3] Memory pool end. avail mem=11.46 GB
[2026-07-01 15:19:55 TP6] KV Cache is allocated. dtype: torch.bfloat16, #tokens: 387968, K size: 5.92 GB, V size: 5.92 GB
[2026-07-01 15:19:55 TP6] Memory pool end. avail mem=11.23 GB
[2026-07-01 15:19:55 TP13] Disable prefill CUDA graph because cuda_graph_config resolved prefill.backend='disabled' (e.g. via --cuda-graph-backend-prefill=disabled or auto-disable rules).
[2026-07-01 15:19:55 TP3] Disable prefill CUDA graph because cuda_graph_config resolved prefill.backend='disabled' (e.g. via --cuda-graph-backend-prefill=disabled or auto-disable rules).
[2026-07-01 15:19:55 TP4] Disable prefill CUDA graph because cuda_graph_config resolved prefill.backend='disabled' (e.g. via --cuda-graph-backend-prefill=disabled or auto-disable rules).
[2026-07-01 15:19:55 TP13] Tree cache initialized: source=default impl=ChunkCache hybrid_swa=False hybrid_ssm=False hierarchical=False streaming_wrapped=False
[2026-07-01 15:19:55 TP3] Tree cache initialized: source=default impl=ChunkCache hybrid_swa=False hybrid_ssm=False hierarchical=False streaming_wrapped=False
[2026-07-01 15:19:55 TP4] Tree cache initialized: source=default impl=ChunkCache hybrid_swa=False hybrid_ssm=False hierarchical=False streaming_wrapped=False
[2026-07-01 15:19:55 TP1] KV Cache is allocated. dtype: torch.bfloat16, #tokens: 387968, K size: 5.92 GB, V size: 5.92 GB
[2026-07-01 15:19:55 TP1] Memory pool end. avail mem=11.46 GB
[2026-07-01 15:19:55 TP8] KV Cache is allocated. dtype: torch.bfloat16, #tokens: 387968, K size: 5.92 GB, V size: 5.92 GB
[2026-07-01 15:19:55 TP8] Memory pool end. avail mem=11.22 GB
[2026-07-01 15:19:55 TP6] Disable prefill CUDA graph because cuda_graph_config resolved prefill.backend='disabled' (e.g. via --cuda-graph-backend-prefill=disabled or auto-disable rules).
[2026-07-01 15:19:55 TP6] Tree cache initialized: source=default impl=ChunkCache hybrid_swa=False hybrid_ssm=False hierarchical=False streaming_wrapped=False
[2026-07-01 15:19:55 TP1] Disable prefill CUDA graph because cuda_graph_config resolved prefill.backend='disabled' (e.g. via --cuda-graph-backend-prefill=disabled or auto-disable rules).
[2026-07-01 15:19:55 TP1] Tree cache initialized: source=default impl=ChunkCache hybrid_swa=False hybrid_ssm=False hierarchical=False streaming_wrapped=False
[2026-07-01 15:19:55 TP8] Disable prefill CUDA graph because cuda_graph_config resolved prefill.backend='disabled' (e.g. via --cuda-graph-backend-prefill=disabled or auto-disable rules).
[2026-07-01 15:19:55 TP8] Tree cache initialized: source=default impl=ChunkCache hybrid_swa=False hybrid_ssm=False hierarchical=False streaming_wrapped=False
[2026-07-01 15:19:55 TP11] KV Cache is allocated. dtype: torch.bfloat16, #tokens: 387968, K size: 5.92 GB, V size: 5.92 GB
[2026-07-01 15:19:55 TP11] Memory pool end. avail mem=11.46 GB
[2026-07-01 15:19:55 TP11] Disable prefill CUDA graph because cuda_graph_config resolved prefill.backend='disabled' (e.g. via --cuda-graph-backend-prefill=disabled or auto-disable rules).
[2026-07-01 15:19:55 TP11] Tree cache initialized: source=default impl=ChunkCache hybrid_swa=False hybrid_ssm=False hierarchical=False streaming_wrapped=False
[2026-07-01 15:19:55] INFO:     Started server process [531603]
[2026-07-01 15:19:55] INFO:     Waiting for application startup.
[2026-07-01 15:19:55] INFO:     Application startup complete.
[2026-07-01 15:19:55] INFO:     Uvicorn running on http://127.0.0.1:21000 (Press CTRL+C to quit)
[2026-07-01 15:19:56] INFO:     127.0.0.1:53300 - "GET /model_info HTTP/1.1" 200 OK
[2026-07-01 15:19:56 TP0] get env HOSTNAME = os-node-created-8fmx9
[2026-07-01 15:19:56 TP13] get env HOSTNAME = os-node-created-8fmx9
[2026-07-01 15:19:56 TP10] get env HOSTNAME = os-node-created-8fmx9
[2026-07-01 15:19:56 TP5] get env HOSTNAME = os-node-created-8fmx9
[2026-07-01 15:19:56 TP12] get env HOSTNAME = os-node-created-8fmx9
[2026-07-01 15:19:56 TP15] get env HOSTNAME = os-node-created-8fmx9
[2026-07-01 15:19:56 TP3] get env HOSTNAME = os-node-created-8fmx9
[2026-07-01 15:19:56 TP8] get env HOSTNAME = os-node-created-8fmx9
[2026-07-01 15:19:56 TP7] get env HOSTNAME = os-node-created-8fmx9
[2026-07-01 15:19:56 TP6] get env HOSTNAME = os-node-created-8fmx9
[2026-07-01 15:19:56 TP4] get env HOSTNAME = os-node-created-8fmx9
[2026-07-01 15:19:56 TP14] get env HOSTNAME = os-node-created-8fmx9
[2026-07-01 15:19:56 TP11] get env HOSTNAME = os-node-created-8fmx9
[2026-07-01 15:19:56 TP2] get env HOSTNAME = os-node-created-8fmx9
[2026-07-01 15:19:56 TP1] get env HOSTNAME = os-node-created-8fmx9
[2026-07-01 15:19:56 TP9] get env HOSTNAME = os-node-created-8fmx9
[2026-07-01 15:20:00 TP11] multimem all-gather disabled (SymmetricMemory does not support device type cuda)
[2026-07-01 15:20:00 TP2] multimem all-gather disabled (SymmetricMemory does not support device type cuda)
[2026-07-01 15:20:00 TP5] multimem all-gather disabled (SymmetricMemory does not support device type cuda)
[2026-07-01 15:20:00 TP1] multimem all-gather disabled (SymmetricMemory does not support device type cuda)
[2026-07-01 15:20:00 TP3] multimem all-gather disabled (SymmetricMemory does not support device type cuda)
[2026-07-01 15:20:00 TP14] multimem all-gather disabled (SymmetricMemory does not support device type cuda)
[2026-07-01 15:20:00 TP8] multimem all-gather disabled (SymmetricMemory does not support device type cuda)
[2026-07-01 15:20:00 TP6] multimem all-gather disabled (SymmetricMemory does not support device type cuda)
[2026-07-01 15:20:00 TP0] multimem all-gather disabled (SymmetricMemory does not support device type cuda)
[2026-07-01 15:20:00 TP12] multimem all-gather disabled (SymmetricMemory does not support device type cuda)
[2026-07-01 15:20:00 TP13] multimem all-gather disabled (SymmetricMemory does not support device type cuda)
[2026-07-01 15:20:00 TP9] multimem all-gather disabled (SymmetricMemory does not support device type cuda)
[2026-07-01 15:20:00 TP15] multimem all-gather disabled (SymmetricMemory does not support device type cuda)
[2026-07-01 15:20:00 TP4] multimem all-gather disabled (SymmetricMemory does not support device type cuda)
[2026-07-01 15:20:00 TP7] multimem all-gather disabled (SymmetricMemory does not support device type cuda)
[2026-07-01 15:20:00 TP10] multimem all-gather disabled (SymmetricMemory does not support device type cuda)
[2026-07-01 15:20:00 TP0] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 22.10
[2026-07-01 15:20:02] INFO:     127.0.0.1:53312 - "POST /v1/chat/completions HTTP/1.1" 200 OK
[2026-07-01 15:20:02] The server is fired up and ready to roll!
[2026-07-01 15:20:03 TP0] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 48.96
[2026-07-01 15:20:04] INFO:     127.0.0.1:34850 - "GET /health_generate HTTP/1.1" 200 OK
[CI Test Method] TestGrok2.test_gsm8k
CompletionSampler initialized with self.model='/data/weights/grok-2' self.temperature=0.0 self.max_tokens=512 self.stop=['Question', 'Assistant:', '<|separator|>']
  0%|                                                                                                                              | 0/200 [00:00<?, ?it/s][2026-07-01 15:20:10 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.02, #running-req: 0, #queue-req: 117, #pending-token: 0, npu graph: False, input throughput (token/s): 124.08
[2026-07-01 15:20:12 TP0] Prefill batch, #new-seq: 10, #new-token: 8192, #cached-token: 0, token usage: 0.04, #running-req: 1, #queue-req: 108, #pending-token: 100174, npu graph: False, input throughput (token/s): 5196.88
[2026-07-01 15:20:13 TP0] Prefill batch, #new-seq: 10, #new-token: 8192, #cached-token: 0, token usage: 0.07, #running-req: 10, #queue-req: 99, #pending-token: 92409, npu graph: False, input throughput (token/s): 5259.32
[2026-07-01 15:20:15 TP0] Prefill batch, #new-seq: 10, #new-token: 8192, #cached-token: 0, token usage: 0.09, #running-req: 19, #queue-req: 90, #pending-token: 84743, npu graph: False, input throughput (token/s): 5173.86
[2026-07-01 15:20:17 TP0] Prefill batch, #new-seq: 10, #new-token: 8192, #cached-token: 0, token usage: 0.11, #running-req: 28, #queue-req: 81, #pending-token: 77037, npu graph: False, input throughput (token/s): 5194.97
[2026-07-01 15:20:18 TP0] Prefill batch, #new-seq: 10, #new-token: 8192, #cached-token: 0, token usage: 0.13, #running-req: 37, #queue-req: 72, #pending-token: 69249, npu graph: False, input throughput (token/s): 5165.49
[2026-07-01 15:20:20 TP0] Prefill batch, #new-seq: 10, #new-token: 8192, #cached-token: 0, token usage: 0.15, #running-req: 46, #queue-req: 63, #pending-token: 61443, npu graph: False, input throughput (token/s): 5204.60
[2026-07-01 15:20:21 TP0] Prefill batch, #new-seq: 10, #new-token: 8192, #cached-token: 0, token usage: 0.17, #running-req: 55, #queue-req: 54, #pending-token: 53658, npu graph: False, input throughput (token/s): 5237.73
[2026-07-01 15:20:23 TP0] Prefill batch, #new-seq: 10, #new-token: 8192, #cached-token: 0, token usage: 0.19, #running-req: 64, #queue-req: 45, #pending-token: 45998, npu graph: False, input throughput (token/s): 5229.51
[2026-07-01 15:20:24 TP0] Prefill batch, #new-seq: 10, #new-token: 8192, #cached-token: 0, token usage: 0.21, #running-req: 73, #queue-req: 35, #pending-token: 38381, npu graph: False, input throughput (token/s): 5070.60
[2026-07-01 15:20:26 TP0] Prefill batch, #new-seq: 10, #new-token: 8192, #cached-token: 0, token usage: 0.23, #running-req: 83, #queue-req: 26, #pending-token: 30628, npu graph: False, input throughput (token/s): 5092.88
[2026-07-01 15:20:28 TP0] Prefill batch, #new-seq: 10, #new-token: 8192, #cached-token: 0, token usage: 0.26, #running-req: 92, #queue-req: 17, #pending-token: 22767, npu graph: False, input throughput (token/s): 5165.23
[2026-07-01 15:20:29 TP0] Prefill batch, #new-seq: 10, #new-token: 8192, #cached-token: 0, token usage: 0.28, #running-req: 101, #queue-req: 8, #pending-token: 15041, npu graph: False, input throughput (token/s): 4861.56
[2026-07-01 15:20:31 TP0] Prefill batch, #new-seq: 10, #new-token: 8192, #cached-token: 0, token usage: 0.30, #running-req: 110, #queue-req: 0, #pending-token: 7280, npu graph: False, input throughput (token/s): 5190.55
[2026-07-01 15:20:39 TP0] Prefill batch, #new-seq: 9, #new-token: 7808, #cached-token: 0, token usage: 0.30, #running-req: 119, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 1018.84
[2026-07-01 15:24:29 TP0] Decode batch, #running-req: 128, #token: 118656, token usage: 0.31, npu graph: False, gen throughput (token/s): 14.47, #queue-req: 0
[2026-07-01 15:26:00] INFO:     127.0.0.1:35030 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:26:10] INFO:     127.0.0.1:35656 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:26:17 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.31, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 2.65
[2026-07-01 15:26:25 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.32, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 111.07
[2026-07-01 15:26:33] INFO:     127.0.0.1:35742 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:26:41] INFO:     127.0.0.1:35826 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:26:48 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.31, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 38.44
[2026-07-01 15:26:56 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.32, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 111.75
[2026-07-01 15:27:05] INFO:     127.0.0.1:35538 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:27:12] INFO:     127.0.0.1:35588 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:27:13] INFO:     127.0.0.1:35120 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:27:13] INFO:     127.0.0.1:35278 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:27:13] INFO:     127.0.0.1:35948 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:27:13 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.31, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 54.24
[2026-07-01 15:27:16 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.32, #running-req: 128, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 357.85
[2026-07-01 15:27:23 TP0] Prefill batch, #new-seq: 3, #new-token: 2688, #cached-token: 0, token usage: 0.32, #running-req: 129, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 343.31
[2026-07-01 15:27:31] INFO:     127.0.0.1:35180 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:27:39] INFO:     127.0.0.1:35322 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:27:39] INFO:     127.0.0.1:35112 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:27:39] INFO:     127.0.0.1:35900 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:27:39] INFO:     127.0.0.1:35902 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:27:40 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.31, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 54.44
[2026-07-01 15:27:40 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.32, #running-req: 128, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 1345.60
[2026-07-01 15:27:48 TP0] Prefill batch, #new-seq: 3, #new-token: 2816, #cached-token: 0, token usage: 0.32, #running-req: 129, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 361.96
[2026-07-01 15:27:56] INFO:     127.0.0.1:35090 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:28:04] INFO:     127.0.0.1:35790 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:28:12 TP0] Prefill batch, #new-seq: 1, #new-token: 1024, #cached-token: 0, token usage: 0.32, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 42.88
[2026-07-01 15:28:12] INFO:     127.0.0.1:35480 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:28:20 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.32, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 108.51
[2026-07-01 15:28:21] INFO:     127.0.0.1:35244 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:28:21] INFO:     127.0.0.1:35306 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:28:21] INFO:     127.0.0.1:35398 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:28:28 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.32, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 112.46
[2026-07-01 15:28:31] INFO:     127.0.0.1:34894 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:28:39 TP0] Prefill batch, #new-seq: 3, #new-token: 2688, #cached-token: 0, token usage: 0.32, #running-req: 125, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 256.23
[2026-07-01 15:28:39] INFO:     127.0.0.1:35164 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:28:39] INFO:     127.0.0.1:35366 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:28:47 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.32, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 111.62
[2026-07-01 15:28:49] INFO:     127.0.0.1:35046 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:28:49] INFO:     127.0.0.1:35522 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:28:57 TP0] Prefill batch, #new-seq: 2, #new-token: 1792, #cached-token: 0, token usage: 0.32, #running-req: 126, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 178.26
[2026-07-01 15:29:05 TP0] Prefill batch, #new-seq: 2, #new-token: 1792, #cached-token: 0, token usage: 0.33, #running-req: 126, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 213.81
[2026-07-01 15:29:13] INFO:     127.0.0.1:35130 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:29:21] INFO:     127.0.0.1:35052 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:29:21] INFO:     127.0.0.1:35218 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:29:21] INFO:     127.0.0.1:35274 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:29:21] INFO:     127.0.0.1:35504 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:29:22] INFO:     127.0.0.1:35286 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:29:22 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.32, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 52.36
[2026-07-01 15:29:23 TP0] Prefill batch, #new-seq: 4, #new-token: 3584, #cached-token: 0, token usage: 0.33, #running-req: 128, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 9701.32
[2026-07-01 15:29:31 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.33, #running-req: 132, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 112.64
[2026-07-01 15:29:39] INFO:     127.0.0.1:35854 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:29:46] INFO:     127.0.0.1:35416 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:29:47 TP0] Decode batch, #running-req: 127, #token: 123904, token usage: 0.32, npu graph: False, gen throughput (token/s): 16.08, #queue-req: 0
[2026-07-01 15:29:47] INFO:     127.0.0.1:35726 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:29:47] INFO:     127.0.0.1:35954 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:29:47 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.32, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 54.55
[2026-07-01 15:29:49 TP0] Prefill batch, #new-seq: 1, #new-token: 1024, #cached-token: 0, token usage: 0.33, #running-req: 128, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 447.26
[2026-07-01 15:29:57 TP0] Prefill batch, #new-seq: 2, #new-token: 1792, #cached-token: 0, token usage: 0.33, #running-req: 129, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 228.10
[2026-07-01 15:30:05] INFO:     127.0.0.1:35802 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:30:13] INFO:     127.0.0.1:35204 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:30:13] INFO:     127.0.0.1:35498 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:30:21 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.32, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 37.91
[2026-07-01 15:30:29 TP0] Prefill batch, #new-seq: 2, #new-token: 1792, #cached-token: 0, token usage: 0.33, #running-req: 126, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 229.77
[2026-07-01 15:30:37] INFO:     127.0.0.1:34972 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:30:37] INFO:     127.0.0.1:35356 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:30:46] INFO:     127.0.0.1:35630 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:30:46 TP0] Prefill batch, #new-seq: 2, #new-token: 1792, #cached-token: 0, token usage: 0.33, #running-req: 126, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 101.09
[2026-07-01 15:30:54 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.33, #running-req: 128, #queue-req: 0, #pending-token:
[2026-07-01 15:31:02] INFO:     127.0.0.1:35402 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:31:10] INFO:     127.0.0.1:35232 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:31:10] INFO:     127.0.0.1:35772 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:31:10] INFO:     127.0.0.1:35836 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:31:18 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.32, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 38.37
[2026-07-01 15:31:26 TP0] Prefill batch, #new-seq: 3, #new-token: 2688, #cached-token: 0, token usage: 0.33, #running-req: 125, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 322.02
[2026-07-01 15:31:34] INFO:     127.0.0.1:35056 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:31:34] INFO:     127.0.0.1:35272 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:31:50 TP0] Prefill batch, #new-seq: 2, #new-token: 1792, #cached-token: 0, token usage: 0.33, #running-req: 126, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 74.73
[2026-07-01 15:32:06] INFO:     127.0.0.1:35428 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:32:06] INFO:     127.0.0.1:35120 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:32:15] INFO:     127.0.0.1:35614 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:32:23 TP0] Prefill batch, #new-seq: 2, #new-token: 1792, #cached-token: 0, token usage: 0.32, #running-req: 126, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 54.31
[2026-07-01 15:32:23] INFO:     127.0.0.1:35034 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:32:23] INFO:     127.0.0.1:35782 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:32:23] INFO:     127.0.0.1:35882 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:32:23] INFO:     127.0.0.1:35886 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:32:31 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.31, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 112.32
[2026-07-01 15:32:39 TP0] Prefill batch, #new-seq: 4, #new-token: 3840, #cached-token: 0, token usage: 0.32, #running-req: 124, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 451.56
[2026-07-01 15:32:47] INFO:     127.0.0.1:34916 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:32:47] INFO:     127.0.0.1:35932 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:32:55] INFO:     127.0.0.1:35012 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:32:55] INFO:     127.0.0.1:35660 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:32:55] INFO:     127.0.0.1:35530 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:32:55] INFO:     127.0.0.1:35546 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:32:56 TP0] Prefill batch, #new-seq: 2, #new-token: 1792, #cached-token: 0, token usage: 0.32, #running-req: 126, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 109.45
[2026-07-01 15:32:56 TP0] Prefill batch, #new-seq: 2, #new-token: 1792, #cached-token: 0, token usage: 0.32, #running-req: 128, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 4111.07
[2026-07-01 15:33:04 TP0] Prefill batch, #new-seq: 2, #new-token: 1792, #cached-token: 0, token usage: 0.32, #running-req: 130, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 226.37
[2026-07-01 15:33:12] INFO:     127.0.0.1:34854 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:33:12] INFO:     127.0.0.1:35556 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:33:20] INFO:     127.0.0.1:35276 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:33:28 TP0] Prefill batch, #new-seq: 2, #new-token: 1920, #cached-token: 0, token usage: 0.32, #running-req: 126, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 80.98
[2026-07-01 15:33:36 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.32, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 107.79
[2026-07-01 15:33:44] INFO:     127.0.0.1:34890 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:33:44] INFO:     127.0.0.1:35618 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:33:53] INFO:     127.0.0.1:35392 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:34:01 TP0] Prefill batch, #new-seq: 2, #new-token: 1792, #cached-token: 0, token usage: 0.32, #running-req: 126, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 72.35
[2026-07-01 15:34:01] INFO:     127.0.0.1:35742 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:34:01] INFO:     127.0.0.1:35802 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:34:09 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.32, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 109.22
[2026-07-01 15:34:10] INFO:     127.0.0.1:35280 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:34:10] INFO:     127.0.0.1:35030 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:34:10] INFO:     127.0.0.1:35656 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:34:17 TP0] Prefill batch, #new-seq: 2, #new-token: 1792, #cached-token: 0, token usage: 0.32, #running-req: 126, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 222.92
[2026-07-01 15:34:18] INFO:     127.0.0.1:35668 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:34:25 TP0] Prefill batch, #new-seq: 3, #new-token: 2688, #cached-token: 0, token usage: 0.32, #running-req: 125, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 325.58
[2026-07-01 15:34:26] INFO:     127.0.0.1:35504 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:34:34 TP0] Prefill batch, #new-seq: 1, #new-token: 896, #cached-token: 0, token usage: 0.32, #running-req: 127, #queue-req: 0, #pending-token: 0, npu graph: False, input throughput (token/s): 109.18
[2026-07-01 15:34:43] INFO:     127.0.0.1:35076 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:34:43] INFO:     127.0.0.1:35696 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:34:50] INFO:     127.0.0.1:35140 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:34:50] INFO:     127.0.0.1:35700 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:34:58] INFO:     127.0.0.1:35480 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:35:13] INFO:     127.0.0.1:35166 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:35:20 TP0] Decode batch, #running-req: 122, #token: 118912, token usage: 0.31, npu graph: False, gen throughput (token/s): 15.20, #queue-req: 0
[2026-07-01 15:35:27] INFO:     127.0.0.1:34984 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:35:27] INFO:     127.0.0.1:35316 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:35:27] INFO:     127.0.0.1:35382 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:35:42] INFO:     127.0.0.1:35804 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:35:57] INFO:     127.0.0.1:35640 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:36:11] INFO:     127.0.0.1:35734 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:36:18] INFO:     127.0.0.1:35278 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:36:25] INFO:     127.0.0.1:35826 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:36:32] INFO:     127.0.0.1:34880 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:36:39] INFO:     127.0.0.1:35466 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:36:46] INFO:     127.0.0.1:35958 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:37:06] INFO:     127.0.0.1:35506 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:37:13] INFO:     127.0.0.1:35664 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:37:19] INFO:     127.0.0.1:35680 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:37:26] INFO:     127.0.0.1:35452 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:37:32] INFO:     127.0.0.1:35294 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:37:32] INFO:     127.0.0.1:35598 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:37:39] INFO:     127.0.0.1:34996 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:37:45] INFO:     127.0.0.1:35714 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:37:52] INFO:     127.0.0.1:35062 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:37:52] INFO:     127.0.0.1:35218 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:37:58] INFO:     127.0.0.1:34972 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:38:04] INFO:     127.0.0.1:35180 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:38:11] INFO:     127.0.0.1:34982 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:38:11] INFO:     127.0.0.1:35208 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:38:11] INFO:     127.0.0.1:35914 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:38:11] INFO:     127.0.0.1:35948 - "POST /v1/completions HTTP/1.1" 200 OK
  0%|▌                                                                                                                | 1/200 [18:06<60:04:26, 1086.77s/it][2026-07-01 15:38:16] INFO:     127.0.0.1:34932 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:38:16] INFO:     127.0.0.1:35790 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:38:22] INFO:     127.0.0.1:35282 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:38:22] INFO:     127.0.0.1:35574 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:38:22] INFO:     127.0.0.1:35954 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:38:28] INFO:     127.0.0.1:35256 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:38:39] INFO:     127.0.0.1:35488 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:38:44] INFO:     127.0.0.1:35774 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:38:44] INFO:     127.0.0.1:35876 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:38:44] INFO:     127.0.0.1:35882 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:38:49] INFO:     127.0.0.1:34852 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:38:49] INFO:     127.0.0.1:35758 - "POST /v1/completions HTTP/1.1" 200 OK
  2%|█▋                                                                                                                | 3/200 [18:45<16:12:28, 296.19s/it][2026-07-01 15:38:55] INFO:     127.0.0.1:35438 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:39:00] INFO:     127.0.0.1:35878 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:39:00] INFO:     127.0.0.1:35428 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:39:04] INFO:     127.0.0.1:34962 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:39:04] INFO:     127.0.0.1:35046 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:39:09] INFO:     127.0.0.1:35336 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:39:09] INFO:     127.0.0.1:35130 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:39:14] INFO:     127.0.0.1:35412 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:39:19] INFO:     127.0.0.1:35104 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:39:19] INFO:     127.0.0.1:35900 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:39:23] INFO:     127.0.0.1:35468 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:39:28 TP0] Decode batch, #running-req: 72, #token: 69888, token usage: 0.18, npu graph: False, gen throughput (token/s): 16.30, #queue-req: 0
[2026-07-01 15:39:28] INFO:     127.0.0.1:35056 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:39:28] INFO:     127.0.0.1:35660 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:39:41] INFO:     127.0.0.1:34960 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:39:41] INFO:     127.0.0.1:35096 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:39:49] INFO:     127.0.0.1:35854 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:02] INFO:     127.0.0.1:34864 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:02] INFO:     127.0.0.1:35186 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:10] INFO:     127.0.0.1:35772 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:10] INFO:     127.0.0.1:35618 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:18] INFO:     127.0.0.1:35322 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:22] INFO:     127.0.0.1:35188 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:22] INFO:     127.0.0.1:35498 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:22] INFO:     127.0.0.1:35530 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:34] INFO:     127.0.0.1:35416 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:41] INFO:     127.0.0.1:35802 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:45] INFO:     127.0.0.1:35346 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:49] INFO:     127.0.0.1:34948 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:52] INFO:     127.0.0.1:35902 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:52] INFO:     127.0.0.1:35232 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:52] INFO:     127.0.0.1:35272 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:56] INFO:     127.0.0.1:35306 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:59] INFO:     127.0.0.1:34854 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:40:59] INFO:     127.0.0.1:35276 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:41:09] INFO:     127.0.0.1:35426 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:41:09] INFO:     127.0.0.1:35280 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:41:12] INFO:     127.0.0.1:34890 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:41:14] INFO:     127.0.0.1:35356 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:41:20] INFO:     127.0.0.1:35522 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:41:23] INFO:     127.0.0.1:35768 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:41:28] INFO:     127.0.0.1:34900 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:41:28] INFO:     127.0.0.1:35588 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:41:28] INFO:     127.0.0.1:34916 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:41:31] INFO:     127.0.0.1:35164 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:41:34] INFO:     127.0.0.1:35286 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:41:36] INFO:     127.0.0.1:35024 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:41:41] INFO:     127.0.0.1:35848 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:41:46 TP0] Decode batch, #running-req: 35, #token: 37120, token usage: 0.10, npu graph: False, gen throughput (token/s): 15.55, #queue-req: 0
[2026-07-01 15:42:02] INFO:     127.0.0.1:35204 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:42:05] INFO:     127.0.0.1:35398 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:42:05] INFO:     127.0.0.1:35932 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:42:07] INFO:     127.0.0.1:35782 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:42:11] INFO:     127.0.0.1:35656 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:42:13] INFO:     127.0.0.1:35052 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:42:13] INFO:     127.0.0.1:35668 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:42:25] INFO:     127.0.0.1:35812 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:42:25] INFO:     127.0.0.1:35630 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:42:25] INFO:     127.0.0.1:35614 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:42:33] INFO:     127.0.0.1:35886 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:42:37] INFO:     127.0.0.1:35090 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:42:41] INFO:     127.0.0.1:35726 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:42:48] INFO:     127.0.0.1:34882 - "POST /v1/completions HTTP/1.1" 200 OK
  2%|██▎                                                                                                               | 4/200 [22:43<15:01:59, 276.12s/it][2026-07-01 15:42:57] INFO:     127.0.0.1:35034 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:43:00 TP0] Decode batch, #running-req: 20, #token: 22272, token usage: 0.06, npu graph: False, gen throughput (token/s): 14.65, #queue-req: 0
[2026-07-01 15:43:09] INFO:     127.0.0.1:35538 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:43:11] INFO:     127.0.0.1:35152 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:43:11] INFO:     127.0.0.1:35392 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:43:11] INFO:     127.0.0.1:35742 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:43:13] INFO:     127.0.0.1:35546 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:43:14] INFO:     127.0.0.1:35570 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:43:16] INFO:     127.0.0.1:35920 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:43:21] INFO:     127.0.0.1:35012 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:43:35] INFO:     127.0.0.1:35868 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:43:35] INFO:     127.0.0.1:35366 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:43:36] INFO:     127.0.0.1:35244 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:43:40] INFO:     127.0.0.1:35148 - "POST /v1/completions HTTP/1.1" 200 OK
 16%|███████████████████▎                                                                                                 | 33/200 [23:36<54:48, 19.69s/it][2026-07-01 15:43:42 TP0] Decode batch, #running-req: 8, #token: 9216, token usage: 0.02, npu graph: False, gen throughput (token/s): 12.74, #queue-req: 0
[2026-07-01 15:43:43] INFO:     127.0.0.1:35556 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:43:46] INFO:     127.0.0.1:35030 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:43:47] INFO:     127.0.0.1:35120 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:43:53] INFO:     127.0.0.1:35112 - "POST /v1/completions HTTP/1.1" 200 OK
 70%|█████████████████████████████████████████████████████████████████████████████████▏                                  | 140/200 [23:49<03:25,  3.42s/it][2026-07-01 15:44:01] INFO:     127.0.0.1:35402 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:44:04 TP0] Decode batch, #running-req: 3, #token: 3456, token usage: 0.01, npu graph: False, gen throughput (token/s): 8.69, #queue-req: 0
[2026-07-01 15:44:22 TP0] Decode batch, #running-req: 3, #token: 3712, token usage: 0.01, npu graph: False, gen throughput (token/s): 6.69, #queue-req: 0
[2026-07-01 15:44:36] INFO:     127.0.0.1:34894 - "POST /v1/completions HTTP/1.1" 200 OK
 74%|██████████████████████████████████████████████████████████████████████████████████████▍                             | 149/200 [24:32<03:00,  3.55s/it][2026-07-01 15:44:39 TP0] Decode batch, #running-req: 2, #token: 2560, token usage: 0.01, npu graph: False, gen throughput (token/s): 6.56, #queue-req: 0
[2026-07-01 15:44:47] INFO:     127.0.0.1:35836 - "POST /v1/completions HTTP/1.1" 200 OK
[2026-07-01 15:44:51 TP0] Decode batch, #running-req: 1, #token: 1280, token usage: 0.00, npu graph: False, gen throughput (token/s): 5.07, #queue-req: 0
[2026-07-01 15:45:00 TP0] Decode batch, #running-req: 1, #token: 1280, token usage: 0.00, npu graph: False, gen throughput (token/s): 4.85, #queue-req: 0
[2026-07-01 15:45:08 TP0] Decode batch, #running-req: 1, #token: 1280, token usage: 0.00, npu graph: False, gen throughput (token/s): 4.90, #queue-req: 0
[2026-07-01 15:45:16 TP0] Decode batch, #running-req: 1, #token: 1408, token usage: 0.00, npu graph: False, gen throughput (token/s): 4.85, #queue-req: 0
[2026-07-01 15:45:22] INFO:     127.0.0.1:35274 - "POST /v1/completions HTTP/1.1" 200 OK
100%|████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 200/200 [25:18<00:00,  7.59s/it]
Total latency: 1518.076 s
Score: 0.935
Output throughput: 14.899 token/s
[METRIC] gsm8k_score=0.935 labels={"model": "/data/weights/grok-2", "eval": "gsm8k"}
[METRIC] gsm8k_latency=1518.076401420869 labels={"model": "/data/weights/grok-2", "eval": "gsm8k"}
Writing report to /tmp/gsm8k__data_weights_grok-2.html
{'score:std': 0.246525860712421, 'score': 0.935, 'latency': 1518.076401420869, 'output_throughput': 14.899118370347043}
Writing results to /tmp/gsm8k__data_weights_grok-2.json
.
----------------------------------------------------------------------
Ran 1 test in 1619.518s

OK

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.



















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28562226227](https://github.com/sgl-project/sglang/actions/runs/28562226227)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28562226064](https://github.com/sgl-project/sglang/actions/runs/28562226064)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
