---
source_id: sglang-github-closed-issues-prs
title: '[Bug] PD disaggregation + Mooncake: sustained load causes KV transfer failures'
canonical_url: https://github.com/sgl-project/sglang/issues/23272
captured_at: '2026-07-01T02:12:08.950785+00:00'
content_hash: cd186143912541b25e6b1c64b239b530777ddb04bc2b9e7e5fc87bb66d93dd17
---
# [Bug] PD disaggregation + Mooncake: sustained load causes KV transfer failures

URL: https://github.com/sgl-project/sglang/issues/23272
State: closed
Labels: inactive
Closed at: 2026-06-30T00:48:51Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

When running PD-disaggregation using SGLang Model Gateway (router) with Mooncake transfer backend, the system becomes unstable under sustained request load (~4 requests/sec). After some time, KV transfer begins failing between prefill and decode workers.

In the same setup, switching the PD transfer backend to `NIXL` (--disaggregation-transfer-backend nixl) resolves the issue

### Reproduction

Step1: Start router in CPU Machine with below command
`python -m sglang_router.launch_router --host 0.0.0.0 --port 8000 --pd-disaggregation`

Step2: Start prefill in GPU Machine (L40s) with below command
```
python -m sglang.launch_server \
            --model-path $MODEL_ID \
            --disaggregation-mode decode \
            --disaggregation-transfer-backend mooncake \
            --host 0.0.0.0 \
            --port 8000
```

Step3: Start decode in another GPU Machine (L40s) with below command
`python -m sglang.launch_server \
            --model-path $MODEL_ID \
            --disaggregation-mode prefill \
            --disaggregation-transfer-backend mooncake \
            --host 0.0.0.0 \
            --port 8000 \
            --disaggregation-bootstrap-port 8998`

Step4: Register prefill and decode workers with rest-api as below
```
# Decode
curl -X POST http://localhost:8000/workers \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://<decode-machine>:8000",
    "worker_type": "decode"
  }'

# Prefill
  curl -X POST http://localhost:8000/workers \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://<prefill-machine>:8000",
    "worker_type": "prefill",
    "bootstrap_port": 8998
  }'

```

Step5: Send `chat/completion` request to router at the rate of 4 Req/s

**Observation**
After sometime below is the error:

**Router Error Output**
```
2026-04-06 12:50:59 ERROR http_request{method=POST uri=/v1/chat/completions version=HTTP/1.0 module="smg" request_id="chatcmpl-DInNanQcl0a3cC0qma4tEQXo"}: smg::routers::http::pd_router: /sgl-workspace/sglang/sgl-model-gateway/src/routers/http/pd_router.rs:172: Failed to select PD pair error=No available prefill workers (all circuits open or unhealthy)
2026-04-06 12:50:59
```

**Decode Worker Error**
```
[2026-04-06 12:49:33] Decode transfer failed for request rank=0 decode_req.req.rid='9904a40eb57148b3b5aac094b8ee78df' decode_req.req.bootstrap_room=5911547551050461423 with exception KVTransferError(bootstrap_room=5911547551050461423): Failed to get kvcache from prefill instance, it might be dead
[2026-04-06 12:49:33] INFO:     192.168.0.45:57586 - "POST /v1/chat/completions HTTP/1.1" 500 Internal Server Error
```


**Prefill Side Error**
```
[2026-04-06 12:50:33] Prefill transfer failed for request rank=0 req.rid='74eed796688843628de7de173376a6ce' req.bootstrap_room=2888068774202995905 with exception KVTransferError(bootstrap_room=2888068774202995905): Decode instance could be dead, remote mooncake session 192.168.0.57:16278 is not alive
[2026-04-06 12:50:33] INFO:     192.168.0.45:38108 - "POST /v1/chat/completions HTTP/1.1" 500 Internal Server Error
[2026-04-06 12:50:34] 192.168
```

**Additional Information:**
We had also tried SGLang Versions 0.5.9 and 0.5.8, but same error persisted.

### Environment

Python: 3.12.3 (main, Mar  3 2026, 12:15:18) [GCC 13.3.0]
CUDA available: True
GPU 0: NVIDIA L40S
GPU 0 Compute Capability: 8.9
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 12.9, V12.9.86
CUDA Driver Version: 580.126.09
PyTorch: 2.9.1+cu129
sglang: 0.5.10.post1
sglang-kernel: 0.4.1
flashinfer_python: 0.6.7.post3
flashinfer_cubin: 0.6.7.post3
flashinfer_jit_cache: 0.6.7.post3+cu129
triton: 3.5.1
transformers: 5.3.0
torchao: 0.9.0
numpy: 2.3.5
aiohttp: 3.13.5
fastapi: 0.135.3
huggingface_hub: 1.9.2
interegular: 0.3.3
modelscope: 1.35.3
orjson: 3.11.8
outlines: 0.1.11
packaging: 26.0
psutil: 7.2.2
pydantic: 2.12.5
python-multipart: 0.0.24
pyzmq: 27.1.0
uvicorn: 0.44.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.1.32
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.92.0
litellm: Module Not Found
torchcodec: 0.9.1
NVIDIA Topology: 
	GPU0	CPU Affinity	NUMA Affinity	GPU NUMA ID
GPU0	 X 	0-7	0		N/A

Legend:

  X    = Self
  SYS  = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
  NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
  PHB  = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)
  PXB  = Connection traversing multiple PCIe bridges (without traversing the PCIe Host Bridge)
  PIX  = Connection traversing at most a single PCIe bridge
  NV#  = Connection traversing a bonded set of # NVLinks

Hypervisor vendor:: KVM
ulimit soft: 1024
