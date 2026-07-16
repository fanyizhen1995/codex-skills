---
source_id: sglang-github-closed-issues-prs
title: '[Bug]  PP is not usable with xgrammar-constrained requests'
canonical_url: https://github.com/sgl-project/sglang/issues/28424
captured_at: '2026-07-11T23:37:37.761819+00:00'
content_hash: 4d91d42e12043be4c2a31b783164ccedf76a926aef1ef9492f6d33f14b023868
---
# [Bug]  PP is not usable with xgrammar-constrained requests

URL: https://github.com/sgl-project/sglang/issues/28424
State: closed
Labels: 
Closed at: 2026-07-11T18:54:51Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

## Summary

Pipeline parallelism is currently unsafe for requests that require xgrammar participation. This includes function/tool-call constraints, structured `response_format`, and other grammar-constrained generation paths.

The failure is caused by grammar compilation readiness being decided independently on each PP scheduler rank. Currently, grammar readiness is synchronized across TP ranks, but not across PP ranks. Since xgrammar compilation latency can differ across processes, one PP rank may finish compiling a request's grammar earlier, move that request from `grammar_queue` to `waiting_queue`, and select it for prefill. Other PP ranks may not consider the same request ready yet, so they select a different batch or no batch.

This breaks the fundamental PP invariant that all pipeline stages must run the same logical request batch in the same order. The result is a PP scheduling divergence, which can lead to deadlock or proxy tensor shape mismatches.

<img width="876" height="1081" alt="Image" src="https://github.com/user-attachments/assets/f4b5086d-0d67-4671-ab40-8c4f44288fe9" />

## Impact

PP is effectively not usable for real production traffic that contains xgrammar-constrained requests. Any workload using function calls, strict tools, named tool choice, required tool choice, or structured response formats can trigger PP scheduling divergence.

More and more models—like GLM-5.1 and DeepSeek-V4-Pro—rely on Pipeline Parallelism (PP) for serving. Given that TP16 is relatively inefficient, if PP remains unavailable, it will be impossible to operationalize these models in production environments.

## Environment

- SGLang server launched with pipeline parallelism:

### Reproduction

python3 -m sglang.launch_server \
  --model-path /data/Qwen3-235B-A22B-Instruct-2507-FP8 \
  --context-length 131072 \
  --host 0.0.0.0 \
  --port 8000 \
  --mem-fraction-static 0.8 \
  --pp-size 4 \
  --log-requests \
  --log-requests-level 1 \
  --enable-metrics \
  --enable-cache-report \
  --tool-call-parser qwen25 \
  --cuda-graph-max-bs 64 \
  --watchdog-timeout 60

### Environment

Python: 3.12.3 (main, Mar 23 2026, 19:04:32) [GCC 13.3.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA H800
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 13.0, V13.0.88
CUDA Driver Version: 550.144.03
PyTorch: 2.11.0+cu130
sglang: 0.0.0.dev1+g11605767e.d20260615
sglang-kernel: 0.4.3
flashinfer_python: 0.6.12
flashinfer_cubin: 0.6.12
flashinfer_jit_cache: Module Not Found
triton: 3.6.0
transformers: 5.8.1
torchao: 0.17.0+cu130
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
pydantic: 2.13.4
python-multipart: 0.0.30
pyzmq: 27.1.0
uvicorn: 0.49.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.2.1
openai: 2.6.1
tiktoken: 0.13.0
anthropic: 0.105.2
litellm: Module Not Found
torchcodec: 0.11.1+cu130
NVIDIA Topology:
        GPU0    GPU1    GPU2    GPU3    GPU4    GPU5    GPU6    GPU7    NIC0    NIC1    NIC2    NIC3    NIC4    NIC5    NIC6    NIC7    NIC8    CPU Affinity    NUMA Affinity   GPU NUMA ID
GPU0     X      NV8     NV8     NV8     NV8     NV8     NV8     NV8     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     NODE    0-55,112-167    0               N/A
GPU1    NV8      X      NV8     NV8     NV8     NV8     NV8     NV8     NODE    PIX     NODE    NODE    SYS     SYS     SYS     SYS     NODE    0-55,112-167    0               N/A
GPU2    NV8     NV8      X      NV8     NV8     NV8     NV8     NV8     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    0-55,112-167    0               N/A
GPU3    NV8     NV8     NV8      X      NV8     NV8     NV8     NV8     NODE    NODE    NODE    PIX     SYS     SYS     SYS     SYS     NODE    0-55,112-167    0               N/A
GPU4    NV8     NV8     NV8     NV8      X      NV8     NV8     NV8     SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     56-111,168-223  1               N/A
GPU5    NV8     NV8     NV8     NV8     NV8      X      NV8     NV8     SYS     SYS     SYS     SYS     NODE    PIX     NODE    NODE    SYS     56-111,168-223  1               N/A
GPU6    NV8     NV8     NV8     NV8     NV8     NV8      X      NV8     SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     56-111,168-223  1               N/A
GPU7    NV8     NV8     NV8     NV8     NV8     NV8     NV8      X      SYS     SYS     SYS     SYS     NODE    NODE    NODE    PIX     SYS     56-111,168-223  1               N/A
NIC0    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS      X      NODE    NODE    NODE    SYS     SYS     SYS     SYS     NODE
NIC1    NODE    PIX     NODE    NODE    SYS     SYS     SYS     SYS     NODE     X      NODE    NODE    SYS     SYS     SYS     SYS     NODE
NIC2    NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE     X      NODE    SYS     SYS     SYS     SYS     NODE
NIC3    NODE    NODE    NODE    PIX     SYS     SYS     SYS     SYS     NODE    NODE    NODE     X      SYS     SYS     SYS     SYS     NODE
NIC4    SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS      X      NODE    NODE    NODE    SYS
NIC5    SYS     SYS     SYS     SYS     NODE    PIX     NODE    NODE    SYS     SYS     SYS     SYS     NODE     X      NODE    NODE    SYS
NIC6    SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE     X      NODE    SYS
NIC7    SYS     SYS     SYS     SYS     NODE    NODE    NODE    PIX     SYS     SYS     SYS     SYS     NODE    NODE    NODE     X      SYS
NIC8    NODE    NODE    NODE    NODE    SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    SYS     SYS     SYS     SYS      X

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
  NIC1: mlx5_3
  NIC2: mlx5_4
  NIC3: mlx5_5
  NIC4: mlx5_6
  NIC5: mlx5_7
  NIC6: mlx5_8
  NIC7: mlx5_9
  NIC8: mlx5_bond_0


ulimit soft: 1048576
