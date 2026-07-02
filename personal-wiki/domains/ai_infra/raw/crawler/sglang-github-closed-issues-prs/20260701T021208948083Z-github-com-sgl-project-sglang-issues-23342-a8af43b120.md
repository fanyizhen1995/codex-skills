---
source_id: sglang-github-closed-issues-prs
title: '[Bug] PD disaggregation (ROCm MI300x) + Mooncake(TCP): /v1/chat/completions
  hangs indefinitely'
canonical_url: https://github.com/sgl-project/sglang/issues/23342
captured_at: '2026-07-01T02:12:08.948083+00:00'
content_hash: a8af43b1205118df5263e36259aea550c995ad1668f1bd7965b8275fa025e60f
---
# [Bug] PD disaggregation (ROCm MI300x) + Mooncake(TCP): /v1/chat/completions hangs indefinitely

URL: https://github.com/sgl-project/sglang/issues/23342
State: closed
Labels: inactive
Closed at: 2026-07-01T00:51:32Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

In PD-disaggregation with Mooncake transfer backend (TCP, no RDMA), requests to the router hang indefinitely. Prefill/decode workers show as healthy and TCP connectivity to the prefill bootstrap port is confirmed.

[router.log](https://github.com/user-attachments/files/26923674/router.log)
[decode.log](https://github.com/user-attachments/files/26923676/decode.log)
[prefill.log](https://github.com/user-attachments/files/26923675/prefill.log)

### Reproduction

Setup: 
Machine1: MI300x (IP:23.183.40.67) runs Prefill Server Container and Router Container
Machine2: MI300x (IP:23.183.40.81) runs Decode Server Container

Network Tests
From DECODE Machine
```
nc -vz <PREFILL_IP> 8998
Connection to <PREFILL_IP> 8998 port [tcp/*] succeeded!
```

```
nc -vz <PREFILL_IP> 8000
Connection to <PREFILL_IP> 8000 port [tcp/*] succeeded!
```

From PREFILL Machine
```
nc -vz <DECODE_IP> 8000
Connection to <PREFILL_IP> 8000 port [tcp/*] succeeded!
```



Step1: Run SGLang Container
```
docker run --rm -it \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add video \
  --ipc=host \
  --network=host \
  lmsysorg/sglang:v0.5.7-rocm700-mi30x \
  bash

```

Step2 : Run Prefill and Decode servers

Prefill:
```
pip install mooncake
export MODEL_ID=meta-llama/Meta-Llama-3-70B-Instruct
export HF_TOKEN=<>
python -m sglang.launch_server \
            --model-path $MODEL_ID \
            --disaggregation-transfer-backend mooncake \
            --host 0.0.0.0 \
            --port 8000 \
            --disaggregation-mode prefill \
            --disaggregation-bootstrap-port 8998
```

Decode:
```
pip install mooncake
export MODEL_ID=meta-llama/Meta-Llama-3-70B-Instruct
export HF_TOKEN=<>
python -m sglang.launch_server \
            --model-path $MODEL_ID \
            --disaggregation-mode decode \
            --disaggregation-transfer-backend mooncake \
            --host 0.0.0.0 \
            --port 8000
```


Router
```
pip install sglang_router
python -m sglang_router.launch_router --host 0.0.0.0 --port 20000 --pd-disaggregation --prefill-policy cache_aware
```


Step3: Register Prefill/Decode Workers in Router using REST API

Prefill
```
curl -X POST http://localhost:20000/workers \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://<PREFILL_IP>:8000",
    "worker_type": "prefill",
    "bootstrap_port": 8998
  }'
```

DECODE
```
curl -X POST http://localhost:20000/workers \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://<DECODE_IP>:8000",
    "worker_type": "decode"
  }'
```

Step4: Check If workers are registered
```
curl http://localhost:20000/workers
{"workers":[{"id":"28e56707-7db1-4bc0-8e6e-0260690e773d","url":"http://23.183.40.81:8000","model_id":"meta-llama/Meta-Llama-3-70B-Instruct","priority":50,"cost":1.0,"worker_type":"decode","is_healthy":true,"load":0,"connection_mode":"HTTP","metadata":{"model_type":"llama","served_model_name":"meta-llama/Meta-Llama-3-70B-Instruct","architectures":"[\"LlamaForCausalLM\"]","model_path":"meta-llama/Meta-Llama-3-70B-Instruct"}},{"id":"74cf329a-311b-4029-b122-0c79566e81d6","url":"http://23.183.40.67:8000","model_id":"meta-llama/Meta-Llama-3-70B-Instruct","priority":50,"cost":1.0,"worker_type":"prefill","is_healthy":true,"load":0,"connection_mode":"HTTP","bootstrap_port":8998,"metadata":{"served_model_name":"meta-llama/Meta-Llama-3-70B-Instruct","model_type":"llama","model_path":"meta-llama/Meta-Llama-3-70B-Instruct","architectures":"[\"LlamaForCausalLM\"]"}}],"total":2,"stats":{"prefill_count":1,"decode_count":1,"regular_count":0}}
```

Step5: Send Request
```
curl -sv --max-time 20 http://localhost:20000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Meta-Llama-3-70B-Instruct",
    "messages": [{"role": "user", "content": "Say hi"}],
    "temperature": 0,
    "max_tokens": 8
  }'
```

Observation
`/v1/chat/completions` does not return (hangs until client cancels). After Ctrl+C logs show below:

From prefill
`Prefill bootstrap failed for request rank=0 req.rid='894df0a757e04ae3b19e360e86055b6d' req.bootstrap_room=389535395827821955 with exception KVTransferError(bootstrap_room=389535395827821955): Aborted by AbortReq.`

From decode
`Decode transfer failed for request rank=0 decode_req.req.rid='909f00550fe5489d8ded220c9d8be263' decode_req.req.bootstrap_room=6531607133299052019 with exception KVTransferError(bootstrap_room=6531607133299052019): Aborted by AbortReq.`


### Environment

Python: 3.10.12 (main, May 27 2025, 17:12:29) [GCC 11.4.0]
ROCM available: True
GPU 0: 
GPU 0 Compute Capability: 9.4
ROCM_HOME: /opt/rocm
HIPCC: HIP version: 7.0.51831-a3e329ad8
ROCM Driver Version: 6.16.13
PyTorch: 2.9.0a0+git7bcbafe
sglang: 0.5.7
sgl_kernel: 0.3.20
flashinfer_python: Module Not Found
flashinfer_cubin: Module Not Found
flashinfer_jit_cache: Module Not Found
triton: 3.4.0+git02502c86
transformers: 4.57.1
torchao: 0.9.0
numpy: 1.26.4
aiohttp: 3.12.15
fastapi: 0.116.1
hf_transfer: 0.1.9
huggingface_hub: 0.34.4
interegular: 0.3.3
modelscope: 1.33.0
orjson: 3.11.5
outlines: 0.1.11
packaging: 25.0
psutil: 7.0.0
pydantic: 2.11.7
python-multipart: 0.0.20
pyzmq: 27.0.2
uvicorn: 0.35.0
uvloop: 0.21.0
vllm: 0.9.2rc2.dev2065+g4f43dae12.rocm700
xgrammar: 0.1.27
openai: 2.6.1
tiktoken: 0.11.0
anthropic: 0.75.0
litellm: Module Not Found
decord2: 3.0.0
AMD Topology: 


============================ ROCm System Management Interface ============================
=============================== Link Type between two GPUs ===============================
       GPU0         
GPU0   0            
================================== End of ROCm SMI Log ===================================

Hypervisor vendor:: KVM
ulimit soft: 1024
