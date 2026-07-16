---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Unexpected KVPoll.Bootstrapping state in process_disagg_prefill_inflight_queue'
canonical_url: https://github.com/sgl-project/sglang/issues/25063
captured_at: '2026-07-13T23:40:05.157077+00:00'
content_hash: a5031efe203c41297598a254fb7cb64d9559e072a9f2b8587d91ab46c9f1e738
---
# [Bug] Unexpected KVPoll.Bootstrapping state in process_disagg_prefill_inflight_queue

URL: https://github.com/sgl-project/sglang/issues/25063
State: closed
Labels: inactive
Closed at: 2026-07-13T00:36:18Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

Related PR: https://github.com/sgl-project/sglang/pull/24967

In disaggregated prefill with the mooncake transfer backend, process_disagg_prefill_inflight_queue can occasionally observe KVPoll.Bootstrapping for a request that is already in disagg_prefill_inflight_queue.

This is unexpected because pop_bootstrapped() keeps requests in the bootstrap queue while their poll state is KVPoll.Bootstrapping. A request should only leave the bootstrap queue after the backend reports a non-bootstrap state, typically KVPoll.WaitingForInput.

When this happens, SGLang emits a warning similar to:

Unexpected polling state 1 for rid <rid> in inflight queue; treating as undone

The request is treated as undone and may still complete normally later. However, the state itself appears inconsistent and should be investigated.

Potential areas to inspect:

bootstrap_room lifecycle and possible reuse/collision
mooncake request_status[bootstrap_room] updates
whether an old inflight sender can observe a newly-created Bootstrapping status for the same bootstrap_room
poll aggregation behavior in poll_and_all_reduce_attn_cp_tp_group


### Reproduction

[disagg_4p1d_simple.sh](https://github.com/user-attachments/files/27627205/disagg_4p1d_simple.sh)

```bash
curl -X POST http://{ip}:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen35-122b",
    "messages": [
      {
        "role": "system",
        "content": "你是一个AI助手"
      },
      {
        "role": "user", 
        "content": "你好"
      }
    ],
    "stream": false,
    "temperature": 0.9,
    "max_tokens": 16,
    "chat_template_kwargs": {
      "enable_thinking": false
    }
  }'
```


## Environment
```
Python: 3.12.3 (main, Mar  3 2026, 12:15:18) [GCC 13.3.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA H800
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 12.9, V12.9.86
CUDA Driver Version: 550.163.01
PyTorch: 2.9.1+cu129
sglang: 0.5.10.post1
sglang-kernel: 0.4.1
flashinfer_python: 0.6.7.post3
flashinfer_cubin: 0.6.7.post3
flashinfer_jit_cache: 0.6.7.post3+cu129
triton: 3.5.1
transformers: 5.3.0
torchao: 0.9.0
numpy: 2.4.4
aiohttp: 3.13.5
fastapi: 0.120.1
huggingface_hub: 1.13.0
interegular: 0.3.3
modelscope: 1.35.3
orjson: 3.11.8
outlines: 0.1.11
packaging: 26.2
psutil: 7.0.0
pydantic: 2.12.5
python-multipart: 0.0.24
pyzmq: 26.4.0
uvicorn: 0.38.0
uvloop: 0.21.0
vllm: Module Not Found
xgrammar: 0.1.32
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.92.0
litellm: Module Not Found
torchcodec: 0.9.1
NVIDIA Topology: 
        GPU0    GPU1    GPU2    GPU3    GPU4    GPU5    GPU6    GPU7    NIC0    NIC1    NIC2    NIC3    NIC4    NIC5    NIC6    NIC7    NIC8    NIC9    NIC10   CPU Affinity    NUMA Affinity   GPU NUMA ID
GPU0     X      NV8     NV8     NV8     NV8     NV8     NV8     NV8     SYS     PIX     PHB     PHB     PHB     SYS     SYS     SYS     SYS     SYS     SYS     0-89    0               N/A
GPU1    NV8      X      NV8     NV8     NV8     NV8     NV8     NV8     SYS     PHB     PIX     PHB     PHB     SYS     SYS     SYS     SYS     SYS     SYS     0-89    0               N/A
GPU2    NV8     NV8      X      NV8     NV8     NV8     NV8     NV8     SYS     PHB     PHB     PIX     PHB     SYS     SYS     SYS     SYS     SYS     SYS     0-89    0               N/A
GPU3    NV8     NV8     NV8      X      NV8     NV8     NV8     NV8     SYS     PHB     PHB     PHB     PIX     SYS     SYS     SYS     SYS     SYS     SYS     0-89    0               N/A
GPU4    NV8     NV8     NV8     NV8      X      NV8     NV8     NV8     SYS     SYS     SYS     SYS     SYS     PIX     PHB     PHB     PHB     SYS     SYS     90-179  1               N/A
GPU5    NV8     NV8     NV8     NV8     NV8      X      NV8     NV8     SYS     SYS     SYS     SYS     SYS     PHB     PIX     PHB     PHB     SYS     SYS     90-179  1               N/A
GPU6    NV8     NV8     NV8     NV8     NV8     NV8      X      NV8     SYS     SYS     SYS     SYS     SYS     PHB     PHB     PIX     PHB     SYS     SYS     90-179  1               N/A
GPU7    NV8     NV8     NV8     NV8     NV8     NV8     NV8      X      SYS     SYS     SYS     SYS     SYS     PHB     PHB     PHB     PIX     SYS     SYS     90-179  1               N/A
NIC0    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS      X      SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS
NIC1    PIX     PHB     PHB     PHB     SYS     SYS     SYS     SYS     SYS      X      PHB     PHB     PHB     SYS     SYS     SYS     SYS     SYS     SYS
NIC2    PHB     PIX     PHB     PHB     SYS     SYS     SYS     SYS     SYS     PHB      X      PHB     PHB     SYS     SYS     SYS     SYS     SYS     SYS
NIC3    PHB     PHB     PIX     PHB     SYS     SYS     SYS     SYS     SYS     PHB     PHB      X      PHB     SYS     SYS     SYS     SYS     SYS     SYS
NIC4    PHB     PHB     PHB     PIX     SYS     SYS     SYS     SYS     SYS     PHB     PHB     PHB      X      SYS     SYS     SYS     SYS     SYS     SYS
NIC5    SYS     SYS     SYS     SYS     PIX     PHB     PHB     PHB     SYS     SYS     SYS     SYS     SYS      X      PHB     PHB     PHB     SYS     SYS
NIC6    SYS     SYS     SYS     SYS     PHB     PIX     PHB     PHB     SYS     SYS     SYS     SYS     SYS     PHB      X      PHB     PHB     SYS     SYS
NIC7    SYS     SYS     SYS     SYS     PHB     PHB     PIX     PHB     SYS     SYS     SYS     SYS     SYS     PHB     PHB      X      PHB     SYS     SYS
NIC8    SYS     SYS     SYS     SYS     PHB     PHB     PHB     PIX     SYS     SYS     SYS     SYS     SYS     PHB     PHB     PHB      X      SYS     SYS
NIC9    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS      X      PHB
NIC10   SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     PHB      X 

Legend:

  X    = Self
  SYS  = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
  NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
  PHB  = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)
  PXB  = Connection traversing multiple PCIe bridges (without traversing the PCIe Host Bridge)
  PIX  = Connection traversing at most a single PCIe bridge
  NV#  = Connection traversing a bonded set of # NVLinks

NIC Legend:

  NIC0: mlx5_0
  NIC1: mlx5_1
  NIC2: mlx5_2
  NIC3: mlx5_3
  NIC4: mlx5_4
  NIC5: mlx5_5
  NIC6: mlx5_6
  NIC7: mlx5_7
  NIC8: mlx5_8
  NIC9: mlx5_9
  NIC10: mlx5_10


Hypervisor vendor:: KVM
ulimit soft: 1048576
```
