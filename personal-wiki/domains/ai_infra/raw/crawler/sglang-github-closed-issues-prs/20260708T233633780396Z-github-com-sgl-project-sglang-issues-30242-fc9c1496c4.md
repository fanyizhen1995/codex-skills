---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Deepseek V4 NVFP4 Disagg Decode node failure'
canonical_url: https://github.com/sgl-project/sglang/issues/30242
captured_at: '2026-07-08T23:36:33.780396+00:00'
content_hash: fc9c1496c4797590aa33e05517aae788111095d473329557c8c91de80ca5b86d
---
# [Bug] Deepseek V4 NVFP4 Disagg Decode node failure

URL: https://github.com/sgl-project/sglang/issues/30242
State: closed
Labels: 
Closed at: 2026-07-08T21:34:51Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [ ] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [ ] Please use English. Otherwise, it will be closed.

### Describe the bug

Error log:

```
2026-07-06T02:45:29.886032Z  INFO dynamo_runtime::pipeline::network::ingress::nats_server: Registering NATS endpoint endpoint_name=load_lora endpoint_with_id=load_lora-694d9f35473aca0f namespace=dynamo component=backend instance_id=7587895998366272015
2026-07-06T02:45:29.886069Z  INFO dynamo_runtime::pipeline::network::ingress::nats_server: Starting NATS push endpoint listener (blocking) endpoint_name=load_lora endpoint_with_id=load_lora-694d9f35473aca0f
2026-07-06T02:45:29.923854Z  INFO _core: Registered base model 'deepseek-ai/DeepSeek-V4-Pro' MDC
[2026-07-05 19:45:29.924] Successfully registered LLM with runtime config
[2026-07-05 19:45:29.924] Model registration succeeded; processing queued requests
[2026-07-05 19:49:44.257 DP1 TP1 EP1] Scheduler hit an exception: Traceback (most recent call last):
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 4274, in run_scheduler_process
    scheduler.run_event_loop()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 1500, in run_event_loop
    dispatch_event_loop(self)
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 4153, in dispatch_event_loop
    scheduler.event_loop_overlap_disagg_decode()
  File "/usr/local/lib/python3.12/dist-packages/torch/utils/_contextlib.py", line 124, in decorate_context
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/disaggregation/decode.py", line 1821, in event_loop_overlap_disagg_decode
    batch_result = self.run_batch(batch)
                   ^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/utils/nvtx_utils.py", line 109, in wrapper
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 3226, in run_batch
    batch_result = self.model_worker.forward_batch_generation(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 541, in forward_batch_generation
    batch_result.next_token_ids = self.model_runner.sample(
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 3144, in sample
    next_token_ids = self.sampler(
                     ^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/torch/nn/modules/module.py", line 1779, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/torch/nn/modules/module.py", line 1790, in _call_impl
    return forward_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/layers/sampler.py", line 128, in forward
    batch_next_token_ids = torch.argmax(logits, -1)
                           ^^^^^^^^^^^^^^^^^^^^^^^^
torch.AcceleratorError: CUDA error: an illegal memory access was encountered
Search for `cudaErrorIllegalAddress' in https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__TYPES.html for more information.
CUDA kernel errors might be asynchronously reported at some other API call, so the stacktrace below might be incorrect.
For debugging consider passing CUDA_LAUNCH_BLOCKING=1
Compile with `TORCH_USE_CUDA_DSA` to enable device-side assertions.
```

After bisection, it is caused by https://github.com/sgl-project/sglang/pull/29461.

nightly-dev-cu13-20260706-8673e85e + revert PR29461 could pass.

### Reproduction

GB300 machine
container: [nightly-dev-cu13-20260706-8673e85e](https://hub.docker.com/layers/lmsysorg/sglang/nightly-dev-cu13-20260706-8673e85e/images/sha256-f950ab6782ea06922c3f5c9236cd43f7d9390793ee9ef58a2ca8477f0e6ba19b)
checkpoints: https://huggingface.co/nvidia/DeepSeek-V4-Pro-NVFP4
Use srtslrum(https://github.com/NVIDIA/srt-slurm) repo to test

Use the following script and repro command is srtctl apply -f nvfp4-disagg-1p1d-dep4-dep16.yaml:override_cutedsl

nvfp4-disagg-1p1d-dep4-dep16.yaml
```
base:
  name: "dsv4-pro-gb300-disagg-1p1d-dep4-dep16-8k1k-nvfp4-trttlm-gen"

  slurm:
    time_limit: "03:00:00"

  model:
    path: "dsv4-pro-nvfp4"
    container: "dev"
    precision: "fp4"

  dynamo:
    hash: "81d0555ee23519cea80a42b4fe824e30368b7300"
    install: true

  resources:
    gpu_type: "gb300"
    gpus_per_node: 4
    prefill_nodes: 1
    prefill_workers: 1
    gpus_per_prefill: 4
    decode_nodes: 4
    decode_workers: 1
    gpus_per_decode: 16

  frontend:
    type: dynamo
    enable_multiple_frontends: false
    env:
      DYN_ROUTER_LOAD_BLOCK_SIZE: "1"
    args:
      router-mode: "kv"
      router-kv-overlap-score-weight: 0
      router-queue-threshold: 64
      router-temperature: 0.5
      no-kv-events: true

  backend:
    type: sglang

    prefill_environment:
      PYTHONUNBUFFERED: "1"
      SGLANG_RADIX_FORCE_MISS: "1"
      SGLANG_JIT_DEEPGEMM_FAST_WARMUP: "1"
      SGLANG_DEFAULT_THINKING: "1"
      SGLANG_DSV4_REASONING_EFFORT: "max"
      SGLANG_OPT_SWA_SPLIT_LEAF_ON_INSERT: "1"
      SGLANG_OPT_SWA_EVICT_DROP_PAGE_MARGIN: "1"
      SGLANG_OPT_USE_ONLINE_COMPRESS: "1"
      NCCL_MNNVL_ENABLE: "1"
      NCCL_CUMEM_ENABLE: "1"
      SGLANG_MOONCAKE_CUSTOM_MEM_POOL: "True"
      MC_FORCE_MNNVL: "1"
      SGLANG_DISAGGREGATION_BOOTSTRAP_TIMEOUT: "100000"
      SGLANG_DISAGGREGATION_WAITING_TIMEOUT: "100000"
      SGLANG_OPT_SWA_RELEASE_LEAF_LOCK_AFTER_WINDOW: "1"
      DYN_SKIP_SGLANG_LOG_FORMATTING: "1"
      SGLANG_LOG_FORWARD_ITERS: "1"
      SGLANG_LOG_MS: "1"
      SGLANG_REQUEST_STATE_WAIT_TIMEOUT: "60"

    decode_environment:
      PYTHONUNBUFFERED: "1"
      SGLANG_RADIX_FORCE_MISS: "1"
      SGLANG_JIT_DEEPGEMM_FAST_WARMUP: "1"
      SGLANG_DEFAULT_THINKING: "1"
      SGLANG_DSV4_REASONING_EFFORT: "max"
      SGLANG_OPT_SWA_SPLIT_LEAF_ON_INSERT: "1"
      SGLANG_OPT_SWA_EVICT_DROP_PAGE_MARGIN: "1"
      SGLANG_OPT_USE_ONLINE_COMPRESS: "1"
      NCCL_MNNVL_ENABLE: "1"
      NCCL_CUMEM_ENABLE: "1"
      SGLANG_MOONCAKE_CUSTOM_MEM_POOL: "True"
      SGLANG_CLIP_MAX_NEW_TOKENS_ESTIMATION: "8"
      MC_FORCE_MNNVL: "1"
      SGLANG_DISAGGREGATION_BOOTSTRAP_TIMEOUT: "100000"
      SGLANG_DISAGGREGATION_WAITING_TIMEOUT: "100000"
      SGLANG_OPT_SWA_RELEASE_LEAF_LOCK_AFTER_WINDOW: "1"
      DYN_SKIP_SGLANG_LOG_FORMATTING: "1"
      SGLANG_LOG_FORWARD_ITERS: "1"
      SGLANG_LOG_MS: "1"
      SGLANG_REQUEST_STATE_WAIT_TIMEOUT: "60"
      SGLANG_FLASHINFER_NUM_MAX_DISPATCH_TOKENS_PER_RANK: "1024"
      SGLANG_MOE_NVFP4_DISPATCH: "1"

    sglang_config:
      prefill:
        served-model-name: "deepseek-ai/DeepSeek-V4-Pro"
        trust-remote-code: true
        watchdog-timeout: 86400
        skip-tokenizer-init: true
        stream-interval: 60

        tensor-parallel-size: 4
        data-parallel-size: 4
        expert-parallel-size: 4

        enable-dp-attention: true
        moe-a2a-backend: "flashinfer"
        moe-runner-backend: "flashinfer_trtllm_routed"
        moe-dense-tp-size: 1
        disable-flashinfer-autotune: true

        disaggregation-mode: "prefill"
        disaggregation-transfer-backend: mooncake

        mem-fraction-static: 0.90
        max-running-requests: 512
        chunked-prefill-size: 32768

      decode:
        served-model-name: "deepseek-ai/DeepSeek-V4-Pro"
        trust-remote-code: true
        watchdog-timeout: 86400
        skip-tokenizer-init: true
        stream-interval: 60

        load-balance-method: "total_requests"
        moe-a2a-backend: "flashinfer"
        moe-runner-backend: "flashinfer_trtllm_routed"
        disable-flashinfer-autotune: true

        disaggregation-mode: "decode"
        disaggregation-transfer-backend: mooncake
        disaggregation-decode-polling-interval: 8

        mem-fraction-static: 0.85
        swa-full-tokens-ratio: 0.056
        context-length: 9216
        tensor-parallel-size: 16
        data-parallel-size: 16
        expert-parallel-size: 16
        enable-dp-attention: true
        enable-dp-lm-head: true
        moe-dense-tp-size: 1
        max-running-requests: 21504
        cuda-graph-max-bs: 256

  benchmark:
    type: "sa-bench"
    isl: 8192
    osl: 1024
    concurrencies: "1024"
    req_rate: "inf"
    use_chat_template: false
    custom_tokenizer: "sa_bench_tokenizers.sglang_deepseek_v4.SGLangDeepseekV4Tokenizer"

override_cutedsl:
  name: "dsv4-pro-gb300-disagg-1p1d-dep4-dep16-8k1k-nvfp4-cutedsl"
  backend:
    sglang_config:
      decode:
        moe-runner-backend: "flashinfer_cutedsl"

override_deepep:
  name: "dsv4-pro-gb300-disagg-1p1d-dep4-dep16-8k1k-nvfp4-deepep"
  backend:
    decode_environment:
      SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK: "512"

    sglang_config:
      decode:
        moe-a2a-backend: "deepep"
        deepep-mode: "low_latency"
        moe-runner-backend: "flashinfer_cutedsl"
```






### Environment

GB300 machine
container: [nightly-dev-cu13-20260706-8673e85e](https://hub.docker.com/layers/lmsysorg/sglang/nightly-dev-cu13-20260706-8673e85e/images/sha256-f950ab6782ea06922c3f5c9236cd43f7d9390793ee9ef58a2ca8477f0e6ba19b)
