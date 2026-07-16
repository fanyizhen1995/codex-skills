---
source_id: sglang-github-closed-issues-prs
title: '[Bug][ROCm][AITER] Qwen3-30B-A3B-Instruct-2507 produces nonsensical output
  on `rocm/sgl-dev:v0.5.11-rocm720-mi35x-20260510` when using AITER attention backend'
canonical_url: https://github.com/sgl-project/sglang/issues/24992
captured_at: '2026-07-11T23:37:37.763905+00:00'
content_hash: 1ce73034b2e8314fd1573fde5dbef35d7a7234898c2f6409974bcd7f356eb2c3
---
# [Bug][ROCm][AITER] Qwen3-30B-A3B-Instruct-2507 produces nonsensical output on `rocm/sgl-dev:v0.5.11-rocm720-mi35x-20260510` when using AITER attention backend

URL: https://github.com/sgl-project/sglang/issues/24992
State: closed
Labels: inactive
Closed at: 2026-07-11T00:33:05Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

Hi,

`Qwen/Qwen3-30B-A3B-Instruct-2507` produces nonsensical outputs when running on Instinct MI350X in either `rocm/sgl-dev:v0.5.11-rocm720-mi35x-20260510`, or in the same container using latest main commit (2e69266f845fd15cd35e692a07d11c8e0c17067b).

### Reproduction

The following:

```
docker run -td --name felix_sglang --rm --device /dev/kfd -e PYTORCH_ROCM_ARCH=gfx950 -e PYTORCH_TUNABLEOP_ENABLED=0 --entrypoint "" --device /dev/dri --device=/dev/cpu -v /sys:/sys:ro --security-opt seccomp=unconfined --shm-size=64g --net host rocm/sgl-dev:v0.5.11-rocm720-mi35x-20260510 /bin/bash
```

Along with:

```bash
sglang serve --model-path Qwen/Qwen3-30B-A3B-Instruct-2507 --tensor-parallel-size 1 --model-loader-extra-config '{"enable_multithread_load": false}' --disable-cuda-graph
```

results in nonsensical output:

```bash
curl http://localhost:30000/v1/completions     -H "Content-Type: application/json"     -d '{
        "model": "Qwen/Qwen3-30B-A3B-Instruct-2507",
        "prompt": "<|im_start|>user\nQuestion: What would you suggest me to do in Paris today? Give 3 suggestions. Answer:<|im_end|>\n<|im_start|>assistant\n",
        "max_tokens": 30,
        "temperature": 0
    }'
```

```
{"id":"64acf19cc26641979c6c6407fdf28367","object":"text_completion","created":1778517315,"model":"Qwen/Qwen3-30B-A3B-Instruct-2507","choices":[{"index":0,"text":"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!","logprobs":null,"finish_reason":"length","matched_stop":null}],"usage":{"prompt_tokens":20,"total_tokens":50,"completion_tokens":30,"prompt_tokens_details":null,"reasoning_tokens":0},"metadata":{"weight_version":"default"}}
```

I don't recall this being the case in previous sglang versions

### Environment

```
WARNING: AMD GPU device(s) is/are in a low-power state. Check power control/runtime_status

Python: 3.10.12 (main, Jan  8 2026, 06:52:19) [GCC 11.4.0]
ROCM available: True
GPU 0,1,2,3,4,5,6,7: AMD Instinct MI350X
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.5
ROCM_HOME: /opt/rocm-7.2.0
HIPCC: HIP version: 7.2.26015-fc0010cf6a
ROCM Driver Version: 6.16.13
PyTorch: 2.9.1+rocm7.2.0.git7e1940d4
sglang: 0.5.11.dev20260510+g2f0686712
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
anthropic: 0.100.0
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

ulimit soft: 1048576
```
