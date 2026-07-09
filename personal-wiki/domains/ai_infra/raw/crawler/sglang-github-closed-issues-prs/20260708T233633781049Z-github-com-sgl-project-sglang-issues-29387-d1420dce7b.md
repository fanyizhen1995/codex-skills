---
source_id: sglang-github-closed-issues-prs
title: '[Bug] GLM-Image AR SRT backend from #25381: single-NPU two-service deployment
  OOMs and multi-NPU deployment fails with `get_image_features` error'
canonical_url: https://github.com/sgl-project/sglang/issues/29387
captured_at: '2026-07-08T23:36:33.781049+00:00'
content_hash: d1420dce7b882ec2063bbf49bba2a189a3c1fb8f4c295401c1bfde3fca11d1fa
---
# [Bug] GLM-Image AR SRT backend from #25381: single-NPU two-service deployment OOMs and multi-NPU deployment fails with `get_image_features` error

URL: https://github.com/sgl-project/sglang/issues/29387
State: closed
Labels: 
Closed at: 2026-07-08T08:46:56Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

I am testing the latest `main` branch with the code from #25381 for the GLM-Image AR SRT backend.

Following the two-service setup described in the PR:

1. start an AR SRT backend service with `vision_language_encoder`
2. start the full GLM-Image diffusion service with `--srt-encoder-url` pointing to the AR backend
3. send `/v1/images/generations` requests to the diffusion service

I encountered two issues:

- Single-NPU deployment: running both services on the same NPU causes OOM.
- Multi-NPU deployment: the request fails with `AttributeError: 'str' object has no attribute 'get_image_features'`.


### Reproduction

### Case 1: Single-NPU deployment OOM
**Start AR SRT backend on port 8764**
```
export HCCL_IF_BASE_PORT=23000
export HCCL_HOST_SOCKET_PORT_RANGE="23000-23199"
export HCCL_NPU_SOCKET_PORT_RANGE="23200-23399"

nohup sglang serve \
  --model-path /nas/disk1/GLM-Image/vision_language_encoder/ \
  --tokenizer-path /nas/disk1/GLM-Image/processor/ \
  --port 8764 \
  --log-level debug \
  --base-gpu-id 6 \
  --tp-size 1 \
  --enable-multimodal \
  --cuda-graph-bs-decode 1 \
  --device npu \
  --attention-backend ascend \
  --mem-fraction-static 0.8 \
  --disable-fast-image-processor \
  --host 0.0.0.0 > ar_server.log 2>&1 &

```
**Start GLM-Image diffusion service on port 8547**
```
export HCCL_IF_BASE_PORT=24000
export HCCL_HOST_SOCKET_PORT_RANGE="24000-24199"
export HCCL_NPU_SOCKET_PORT_RANGE="24200-24399"

export SGLANG_CACHE_DIT_FN=2
export SGLANG_CACHE_DIT_BN=1
export SGLANG_CACHE_DIT_WARMUP=4
export SGLANG_CACHE_DIT_RDT=0.4
export SGLANG_CACHE_DIT_MC=4
export SGLANG_CACHE_DIT_TAYLORSEER=true
export SGLANG_CACHE_DIT_TS_ORDER=2
export SGLANG_CACHE_DIT_ENABLED=true

nohup sglang serve \
  --model-path /nas/disk1/GLM-Image/ \
  --srt-encoder-url http://127.0.0.1:8764 \
  --port 8547 \
  --log-level debug \
  --tp-size 1 \
  --num-gpus 1 \
  --base-gpu-id 6 \
  --host 0.0.0.0 > diffusion_server.log 2>&1 &
```
**Send request**
```
curl http://127.0.0.1:8547/v1/images/generations \
 -H "Content-Type: application/json" \
 -d '{
    "prompt": "a black and white cat wearing a princess tiara",
    "n": 1,
    "size": "1024x1024"
 }'
```

**Actual result**

> The request fails with NPU OOM:
> RuntimeError: Model generation returned no output. Error from scheduler:
> Error executing request ...:
> NPU out of memory. Tried to allocate 34.00 MiB
> NPU 0; 60.96 GiB total capacity;
> 57.76 GiB already allocated;
> 5.76 GiB current active;
> 4.68 MiB free;
> 6.00 GiB reserved in total by PyTorch.

<img width="1900" height="906" alt="Image" src="https://github.com/user-attachments/assets/203804ae-d2c5-461e-8c85-a5d2641c6657" />

### Case 2: Multi-NPU deployment fails with get_image_features error
**Start AR SRT backend on port 8764**
```
export HCCL_IF_BASE_PORT=23000
export HCCL_HOST_SOCKET_PORT_RANGE="23000-23199"
export HCCL_NPU_SOCKET_PORT_RANGE="23200-23399"

nohup sglang serve \
  --model-path /nas/disk1/GLM-Image/vision_language_encoder/ \
  --tokenizer-path /nas/disk1/GLM-Image/processor/ \
  --port 8764 \
  --log-level debug \
  --base-gpu-id 6 \
  --tp-size 2 \
  --enable-multimodal \
  --cuda-graph-bs-decode 1 \
  --device npu \
  --attention-backend ascend \
  --mem-fraction-static 0.8 \
  --disable-fast-image-processor \
  --host 0.0.0.0 > ar_server.log 2>&1 &
```

**Start GLM-Image diffusion service on port 8547**
```
export HCCL_IF_BASE_PORT=24000
export HCCL_HOST_SOCKET_PORT_RANGE="24000-24199"
export HCCL_NPU_SOCKET_PORT_RANGE="24200-24399"

export SGLANG_CACHE_DIT_FN=2
export SGLANG_CACHE_DIT_BN=1
export SGLANG_CACHE_DIT_WARMUP=4
export SGLANG_CACHE_DIT_RDT=0.4
export SGLANG_CACHE_DIT_MC=4
export SGLANG_CACHE_DIT_TAYLORSEER=true
export SGLANG_CACHE_DIT_TS_ORDER=2
export SGLANG_CACHE_DIT_ENABLED=true

nohup sglang serve \
  --model-path /nas/disk1/GLM-Image/ \
  --srt-encoder-url http://127.0.0.1:8764 \
  --port 8547 \
  --log-level debug \
  --tp-size 2 \
  --num-gpus 2 \
  --base-gpu-id 6 \
  --host 0.0.0.0 > diffusion_server.log 2>&1 &
```

**Send request**

```
curl http://127.0.0.1:8547/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a black and white cat wearing a princess tiara",
    "n": 1,
    "size": "1024x1024"
  }'
```

Actual result

<img width="1614" height="943" alt="Image" src="https://github.com/user-attachments/assets/d40c452a-3c95-4f8a-8425-83262d3f013a" />


The two-service setup should work with --srt-encoder-url:
the AR stage should be served by the SRT backend on port 8764
image generation requests should be sent to the diffusion service on port 8547
the request should complete successfully without OOM or get_image_features errors
the GLM-Image AR stage should benefit from the SRT backend introduced in #25381


### Environment

- SGLang: latest `main` + code from #25381
- Model path: `/nas/disk1/GLM-Image/`
- AR model path: `/nas/disk1/GLM-Image/vision_language_encoder/`
- Tokenizer / processor path: `/nas/disk1/GLM-Image/processor/`
- Device: Ascend NPU A2
- Attention backend: `ascend`
- API: `/v1/images/generations`
