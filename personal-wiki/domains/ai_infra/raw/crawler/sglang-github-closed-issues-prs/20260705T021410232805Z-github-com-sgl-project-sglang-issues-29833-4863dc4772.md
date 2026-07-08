---
source_id: sglang-github-closed-issues-prs
title: '[Bug] ValueError: Cannot find any of [''quant_method''] when using online
  quantization, leading to OOM'
canonical_url: https://github.com/sgl-project/sglang/issues/29833
captured_at: '2026-07-05T02:14:10.232805+00:00'
content_hash: 4863dc477276e461bf840374e9c91026b0a7467f4f6ccf8250aad9729902d47b
---
# [Bug] ValueError: Cannot find any of ['quant_method'] when using online quantization, leading to OOM

URL: https://github.com/sgl-project/sglang/issues/29833
State: closed
Labels: 
Closed at: 2026-07-04T15:40:45Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [ ] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

Hello everyone, I would like to ask for help with an issue related to SGLang online quantization.

When I use the command below to perform online quantization and start the service simultaneously, I run into a `ValueError: Cannot find any of ['quant_method']` error, which subsequently causes an OOM (Out of Memory) failure.


I looked up relevant information and consulted the SGLang AI assistant. The reply from the assistant is as follows:
~~~text
This indicates that SGLang cannot find the quantization configuration when attempting online quantization, and then falls back to loading the original BF16 model. The original model is too large, which is the direct cause of the OOM issue.
When using `--quantization fp8` for online quantization, SGLang is expected to handle the configuration automatically. The error suggests that after SGLang's custom loader fails, it falls back to loading the original BF16 model, and the oversized original model results in OOM.
~~~

I wonder if anyone has encountered a similar problem. Any help or guidance would be greatly appreciated. Thank you in advance!

I have written the specific error message to 'sglang_1h3. log', and the specific content is as follows:
~~~shell
Unable to import `torchao` Tensor objects. This may affect loading checkpoints serialized with `torchao`
[07-01 15:19:44] Applying performance_mode=memory
[07-01 15:19:44] Applied low-memory component offload defaults: dit_cpu_offload=True, text_encoder_cpu_offload=True, image_encoder_cpu_offload=True
[07-01 15:19:44] Enabling large component offloading for GPU with low device memory
[93m[07-01 15:19:44] dit_layerwise_offload is enabled: [92mlower GPU memory usage[0;0m, but [91mmay reduce throughput or increase latency[0;0m. [1;36mIf you are using multi-GPU deployment and already have enough memory headroom, prefer keeping dit_layerwise_offload disabled.[0;0m Please tune this based on your memory headroom and performance target.[0;0m
[07-01 15:19:44] server_args: {"model_path": "/root/autodl-fs/data/z-image_turbo/Tongyi-MAI/Z-Image-Turbo", "model_id": null, "backend": "auto", "attention_backend": null, "attention_backend_config": {}, "component_attention_backends": {}, "cache_dit_config": null, "nccl_port": null, "trust_remote_code": false, "revision": null, "num_gpus": 1, "performance_mode": "memory", "tp_size": 1, "sp_degree": 1, "ulysses_degree": 1, "ring_degree": 1, "dp_size": 1, "dp_degree": 1, "enable_cfg_parallel": false, "cfg_parallel_degree": 1, "hsdp_replicate_dim": 1, "hsdp_shard_dim": 1, "dist_timeout": 3600, "pipeline_class_name": null, "lora_path": null, "lora_nickname": "default", "lora_scale": 1.0, "lora_merge_mode": "auto", "lora_weight_name": null, "component_paths": {}, "transformer_weights_path": null, "quantization": "fp8", "quantization_ignored_layers": null, "lora_target_modules": null, "dit_cpu_offload": true, "dit_layerwise_offload": true, "dit_offload_prefetch_size": 0.0, "text_encoder_cpu_offload": true, "image_encoder_cpu_offload": true, "vae_cpu_offload": false, "use_fsdp_inference": false, "pin_cpu_memory": true, "ltx2_two_stage_device_mode": null, "comfyui_mode": false, "enable_torch_compile": false, "warmup": false, "warmup_resolutions": null, "warmup_steps": 1, "disable_autocast": false, "master_port": 30005, "host": "0.0.0.0", "port": 30000, "webui": false, "webui_port": 12312, "scheduler_port": 5648, "batching_mode": "dynamic", "batching_max_size": 1, "batching_delay_ms": 0.0, "batching_config": null, "enable_batching_metrics": false, "strict_ports": false, "output_path": "outputs/", "input_save_path": "inputs/uploads", "prompt_file_path": null, "model_paths": {}, "model_loaded": {"transformer": true, "vae": true, "video_vae": true, "audio_vae": true, "video_dit": true, "audio_dit": true, "dual_tower_bridge": true}, "boundary_ratio": null, "base_gpu_id": 0, "disagg_role": "monolithic", "disagg_timeout": 600, "disagg_dispatch_policy": "round_robin", "disagg_mode": false, "disagg_server_addr": null, "encoder_urls": null, "denoiser_urls": null, "decoder_urls": null, "encoder_tp": null, "denoiser_tp": null, "denoiser_sp": null, "denoiser_ulysses": null, "denoiser_ring": null, "decoder_tp": null, "disagg_transfer_pool_size": 268435456, "disagg_p2p_hostname": "127.0.0.1", "disagg_ib_device": null, "pool_work_endpoint": null, "pool_result_endpoint": null, "log_level": "info", "uvicorn_access_log_exclude_prefixes": [], "enable_trace": false, "otlp_traces_endpoint": "localhost:4317"}
[07-01 15:19:44] Starting server...
Unable to import `torchao` Tensor objects. This may affect loading checkpoints serialized with `torchao`
[07-01 15:19:53] Scheduler bind at endpoint: tcp://0.0.0.0:5648
[07-01 15:19:53] Initializing distributed environment with world_size=1, device=cuda:0, timeout=3600
[07-01 15:19:53] Setting distributed timeout to 3600 seconds
[07-01 15:19:54] No pipeline_class_name specified, using model_index.json
[07-01 15:19:54] Diffusers version: 0.36.0.dev0
[07-01 15:19:54] Using pipeline from model_index.json: ZImagePipeline
[07-01 15:19:54] Loading pipeline modules...
[07-01 15:19:54] Model already exists locally and is complete
[07-01 15:19:54] Model path: /root/autodl-fs/data/z-image_turbo/Tongyi-MAI/Z-Image-Turbo
[07-01 15:19:54] Diffusers version: 0.36.0.dev0
[07-01 15:19:54] Loading pipeline modules from config: {'_class_name': 'ZImagePipeline', '_diffusers_version': '0.36.0.dev0', 'scheduler': ['diffusers', 'FlowMatchEulerDiscreteScheduler'], 'text_encoder': ['transformers', 'Qwen3Model'], 'tokenizer': ['transformers', 'Qwen2Tokenizer'], 'transformer': ['diffusers', 'ZImageTransformer2DModel'], 'vae': ['diffusers', 'AutoencoderKL']}
[07-01 15:19:54] Loading required components: ['text_encoder', 'tokenizer', 'vae', 'transformer', 'scheduler']

Loading required modules:   0%|                                                                                                     | 0/5 [00:00<?, ?it/s][07-01 15:19:54] Loading text_encoder from /root/autodl-fs/data/z-image_turbo/Tongyi-MAI/Z-Image-Turbo/text_encoder. avail mem: 18.46 GB
[07-01 15:19:54] Using FlashAttention (FA3 for hopper, FA4 for blackwell) backend
[07-01 15:19:54] Attention backend not specified for text_encoder, using fa backend for text_encoder
[07-01 15:20:22] [RunAI Streamer] Overall time to stream 7.5 GiB of all files to cpu: 27.86s, 275.4 MiB/s
[07-01 15:20:32] Applied FSDP to 182 submodules in FSDPQwen3ForCausalLM using explicit shard conditions
[07-01 15:20:32] Loaded text_encoder: FSDPQwen3ForCausalLM (sgl-diffusion version). model size: 7.5 GB, consumed GPU mem: 0.03 GB, avail GPU mem: 18.43 GB

Loading required modules:  20%|██████████████████▌                                                                          | 1/5 [00:38<02:35, 38.76s/it][07-01 15:20:32] Loading tokenizer from /root/autodl-fs/data/z-image_turbo/Tongyi-MAI/Z-Image-Turbo/tokenizer. avail mem: 18.43 GB
[07-01 15:20:33] Loaded tokenizer: Qwen2Tokenizer (sgl-diffusion version). model size: NA GB, consumed GPU mem: 0.00 GB, avail GPU mem: 18.43 GB

Loading required modules:  40%|█████████████████████████████████████▏                                                       | 2/5 [00:39<00:49, 16.36s/it][07-01 15:20:33] Loading vae from /root/autodl-fs/data/z-image_turbo/Tongyi-MAI/Z-Image-Turbo/vae. avail mem: 18.43 GB
[07-01 15:20:33] Loaded vae: AutoencoderKL (sgl-diffusion version). model size: 0.31 GB, consumed GPU mem: 0.35 GB, avail GPU mem: 18.08 GB

Loading required modules:  60%|███████████████████████████████████████████████████████▊                                     | 3/5 [00:39<00:17,  8.95s/it][07-01 15:20:33] Loading transformer from /root/autodl-fs/data/z-image_turbo/Tongyi-MAI/Z-Image-Turbo/transformer. avail mem: 18.08 GB
Traceback (most recent call last):
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/loader/component_loaders/component_loader.py", line 138, in load
    component = self.load_customized(
                ^^^^^^^^^^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/loader/component_loaders/transformer_loader.py", line 91, in load_customized
    quant_spec = resolve_transformer_quant_load_spec(
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/loader/transformer_load_utils.py", line 365, in resolve_transformer_quant_load_spec
    quant_config = _resolve_quant_config(
                   ^^^^^^^^^^^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/loader/transformer_load_utils.py", line 495, in _resolve_quant_config
    return quant_cls.from_config({})
           ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/layers/quantization/fp8.py", line 129, in from_config
    quant_method = cls.get_from_keys(config, ["quant_method"])
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/layers/quantization/configs/base_config.py", line 127, in get_from_keys
    raise ValueError(
ValueError: Cannot find any of ['quant_method'] in the model's quantization config.
[91m[07-01 15:20:33] Error while loading customized transformer, falling back to native version[0;0m


Loading checkpoint shards:   0%|                                                                                                    | 0/3 [00:00<?, ?it/s][A
Loading checkpoint shards: 100%|███████████████████████████████████████████████████████████████████████████████████████████| 3/3 [00:00<00:00, 106.98it/s]
[91m[07-01 15:20:37] Error while loading component: transformer, component_model_path='/root/autodl-fs/data/z-image_turbo/Tongyi-MAI/Z-Image-Turbo/transformer'[0;0m

Loading required modules:  60%|███████████████████████████████████████████████████████▊                                     | 3/5 [00:42<00:28, 14.29s/it]
[93m[07-01 15:20:37] 
OOM detected. Possible solutions:
  - If the OOM occurs during loading:
    1. Check available memory on every selected GPU, not only total capacity.
       In multi-GPU runs, the least-free selected GPU is the bottleneck.
    2. For single-GPU deployment, use `--performance-mode memory`, component CPU offload,
       or `--dit-layerwise-offload` for supported Wan/MOVA DiTs.
    3. For multi-GPU deployment, keep the default `--performance-mode auto` or set
       `--use-fsdp-inference true` to shard DiT weights with FSDP. FSDP is not a
       single-GPU substitute for CPU offload.
  - If the OOM occurs during runtime:
    1. Reduce resolution, `--num-frames`, or batch size.
    2. Use `--performance-mode memory` for lower memory usage.
    3. Enable SP/Ulysses/Ring for sequence-heavy workloads in multi-GPU setups.
    4. Use FSDP, with CFG parallelism when supported, for validated multi-GPU workloads.
    5. Use a lower-memory attention backend or quantization when available.
  Or, open an issue on GitHub https://github.com/sgl-project/sglang/issues/new/choose
[0;0m
[07-01 15:20:42] Worker 0: Shutdown complete.
Process sglang-diffusionWorker-0:
Traceback (most recent call last):
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/loader/component_loaders/component_loader.py", line 138, in load
    component = self.load_customized(
                ^^^^^^^^^^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/loader/component_loaders/transformer_loader.py", line 91, in load_customized
    quant_spec = resolve_transformer_quant_load_spec(
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/loader/transformer_load_utils.py", line 365, in resolve_transformer_quant_load_spec
    quant_config = _resolve_quant_config(
                   ^^^^^^^^^^^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/loader/transformer_load_utils.py", line 495, in _resolve_quant_config
    return quant_cls.from_config({})
           ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/layers/quantization/fp8.py", line 129, in from_config
    quant_method = cls.get_from_keys(config, ["quant_method"])
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/layers/quantization/configs/base_config.py", line 127, in get_from_keys
    raise ValueError(
ValueError: Cannot find any of ['quant_method'] in the model's quantization config.

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/root/miniconda3/lib/python3.12/multiprocessing/process.py", line 314, in _bootstrap
    self.run()
  File "/root/miniconda3/lib/python3.12/multiprocessing/process.py", line 108, in run
    self._target(*self._args, **self._kwargs)
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/managers/gpu_worker.py", line 942, in run_scheduler_process
    scheduler = Scheduler(
                ^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/managers/scheduler.py", line 119, in __init__
    worker = Exec_worker(
             ^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/managers/gpu_worker.py", line 113, in __init__
    self.init_device_and_model()
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/managers/gpu_worker.py", line 164, in init_device_and_model
    self.pipeline = build_pipeline(self.server_args)
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/pipelines_core/__init__.py", line 79, in build_pipeline
    pipeline = pipeline_cls(model_path, server_args)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/pipelines_core/lora_pipeline.py", line 72, in __init__
    super().__init__(*args, **kwargs)
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/pipelines_core/composed_pipeline_base.py", line 130, in __init__
    self.modules = self.load_modules(server_args, loaded_modules)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/pipelines_core/composed_pipeline_base.py", line 431, in load_modules
    module, memory_usage = PipelineComponentLoader.load_component(
                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/loader/component_loaders/component_loader.py", line 449, in load_component
    raise e
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/loader/component_loaders/component_loader.py", line 439, in load_component
    return loader.load(
           ^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/loader/component_loaders/component_loader.py", line 161, in load
    component = component.to(device=target_device)
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/diffusers/models/modeling_utils.py", line 1451, in to
    return super().to(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/torch/nn/modules/module.py", line 1384, in to
    return self._apply(convert)
           ^^^^^^^^^^^^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/torch/nn/modules/module.py", line 934, in _apply
    module._apply(fn)
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/torch/nn/modules/module.py", line 934, in _apply
    module._apply(fn)
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/torch/nn/modules/module.py", line 934, in _apply
    module._apply(fn)
  [Previous line repeated 1 more time]
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/torch/nn/modules/module.py", line 965, in _apply
    param_applied = fn(param)
                    ^^^^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/torch/nn/modules/module.py", line 1370, in convert
    return t.to(
           ^^^^^
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 150.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 118.69 MiB is free. Including non-PyTorch memory, this process has 23.37 GiB memory in use. Of the allocated memory 18.10 GiB is allocated by PyTorch, and 220.86 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://docs.pytorch.org/docs/stable/notes/cuda.html#optimizing-memory-usage-with-pytorch-cuda-alloc-conf)
[91m[07-01 15:20:44] Rank 0 scheduler is dead. Please check if there are relevant logs.[0;0m
[91m[07-01 15:20:46] Exit code: 1[0;0m
Traceback (most recent call last):
  File "/root/autodl-tmp/sglang-env/bin/sglang", line 10, in <module>
    sys.exit(main())
             ^^^^^^
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/cli/main.py", line 40, in main
    serve(args, extra_argv)
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/cli/serve.py", line 120, in serve
    execute_serve_cmd(parsed_args, remaining_argv)
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/entrypoints/cli/serve.py", line 37, in execute_serve_cmd
    dispatch_launch(server_args)
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/launch_server.py", line 667, in dispatch_launch
    launch_server(server_args)
  File "/root/autodl-tmp/sglang-env/lib/python3.12/site-packages/sglang/multimodal_gen/runtime/launch_server.py", line 178, in launch_server
    data = reader.recv()
           ^^^^^^^^^^^^^
  File "/root/miniconda3/lib/python3.12/multiprocessing/connection.py", line 250, in recv
    buf = self._recv_bytes()
          ^^^^^^^^^^^^^^^^^^
  File "/root/miniconda3/lib/python3.12/multiprocessing/connection.py", line 430, in _recv_bytes
    buf = self._recv(4)
          ^^^^^^^^^^^^^
  File "/root/miniconda3/lib/python3.12/multiprocessing/connection.py", line 399, in _recv
    raise EOFError
EOFError
~~~


### Reproduction

The specific startup command is as follows:
~~~shell
#!/bin/bash
sglang serve \
   --model-path /root/autodl-fs/data/z-image_turbo/Tongyi-MAI/Z-Image-Turbo \
   --host 0.0.0.0 \
   --port 30000 \
   --quantization fp8 \
   --dit-layerwise-offload \
   --performance-mode memory \
   --batching-max-size 1 \
   2>&1 | tee sglang_lh3.log
~~~

I have tried the method from the official documentation, but the same error still occurs.
Official reference: https://docs.sglang.io/docs/sglang-diffusion/quantization#online-quantization
~~~shell
#!/bin/bash
sglang generate \
   --model-path /root/autodl-fs/data/z-image_turbo/Tongyi-MAI/Z-Image-Turbo \
   --host 0.0.0.0 \
   --port 30000 \
   --quantization fp8 \
   --prompt "a beautiful sunset" \
   --save-output
~~~

The model used is: z-image-turbo

### Environment

(sglang-env) root@autodl-container-9kkpgm5n90-1f7ab3c7:~# python3 -m sglang.check_env
Python: 3.12.3 | packaged by Anaconda, Inc. | (main, May  6 2024, 19:46:43) [GCC 11.2.0]
CUDA available: True
GPU 0: NVIDIA GeForce RTX 4090
GPU 0 Compute Capability: 8.9
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 12.8, V12.8.93
CUDA Driver Version: 580.105.08
PyTorch: 2.11.0+cu130
sglang: 0.5.12.post1
sglang-kernel: 0.4.2.post2
flashinfer_python: 0.6.11.post1
flashinfer_cubin: 0.6.11.post1
flashinfer_jit_cache: Module Not Found
triton: 3.6.0
transformers: 5.6.0
torchao: 0.17.0
numpy: 2.3.5
aiohttp: 3.14.0
fastapi: 0.136.3
huggingface_hub: 1.17.0
interegular: 0.3.3
modelscope: 1.37.1
orjson: 3.11.9
outlines: 0.1.11
packaging: 26.2
psutil: 7.2.2
pydantic: 2.14.0a1
python-multipart: 0.0.30
pyzmq: 27.1.0
uvicorn: 0.48.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.2.0
openai: 2.6.1
tiktoken: 0.13.0
anthropic: 0.105.2
litellm: Module Not Found
torchcodec: 0.11.1
NVIDIA Topology: 
        GPU0    CPU Affinity    NUMA Affinity   GPU NUMA ID
GPU0     X      0-31,64-95      0               N/A

Legend:

  X    = Self
  SYS  = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
  NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
  PHB  = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)
  PXB  = Connection traversing multiple PCIe bridges (without traversing the PCIe Host Bridge)
  PIX  = Connection traversing at most a single PCIe bridge
  NV#  = Connection traversing a bonded set of # NVLinks

ulimit soft: 65535
