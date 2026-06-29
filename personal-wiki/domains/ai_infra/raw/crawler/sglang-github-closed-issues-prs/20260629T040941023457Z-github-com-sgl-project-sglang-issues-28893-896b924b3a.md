---
source_id: sglang-github-closed-issues-prs
title: '[Bug] GLM 5.2 crash with deepep moe a2a backend on H20'
canonical_url: https://github.com/sgl-project/sglang/issues/28893
captured_at: '2026-06-29T04:09:41.023457+00:00'
content_hash: 896b924b3a333d97c4e4d3a3d3a6a4d17402605b0bac2cfc8892e718b59889a9
---
# [Bug] GLM 5.2 crash with deepep moe a2a backend on H20

URL: https://github.com/sgl-project/sglang/issues/28893
State: closed
Labels: 
Closed at: 2026-06-29T01:46:04Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

follow official lanuch command[https://docs.sglang.io/cookbook/autoregressive/GLM/GLM-5.2#hw=h200&variant=default&quant=fp8&strategy=high-throughput&nodes=single]

RuntimeError: CUDA driver exception (/data/workspace/DeepEP-main/csrc/legacy/../utils/shared_memory.hpp:69): 800 (CUDA_ERROR_NOT_PERMITTED, operation not permitted)

### Reproduction

sglang serve   --model-path /data/GLM-5.2-FP8   --tp 8   --dp 8   --enable-dp-attention   --moe-a2a-backend deepep   --mem-fraction-static 0.85   --cuda-graph-max-bs 256   --max-running-requests 256   --host 0.0.0.0   --port 30000

full log is here. [log.txt](https://github.com/user-attachments/files/29193764/log.txt)

### Environment

Python: 3.10.12 (main, Mar  3 2026, 11:56:32) [GCC 11.4.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA H20-3e
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 13.0, V13.0.48
CUDA Driver Version: 580.126.09
PyTorch: 2.11.0+cu130
sglang: 0.5.13.post1
sglang-kernel: 0.4.3
flashinfer_python: 0.6.12
flashinfer_cubin: 0.6.12
flashinfer_jit_cache: Module Not Found
triton: 3.6.0
transformers: 5.8.1
torchao: 0.17.0
numpy: 2.2.6
aiohttp: 3.14.1
fastapi: 0.138.0
huggingface_hub: 1.20.1
interegular: 0.3.3
modelscope: 1.37.1
orjson: 3.11.9
outlines: 0.1.11
packaging: 26.2
psutil: 7.2.2
pydantic: 2.14.0a1
python-multipart: 0.0.32
pyzmq: 27.1.0
uvicorn: 0.49.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.2.1
openai: 2.6.1
tiktoken: 0.13.0
anthropic: 0.111.0
litellm: Module Not Found
torchcodec: 0.11.1
NVIDIA Topology:
        GPU0    GPU1    GPU2    GPU3    GPU4    GPU5    GPU6    GPU7    NIC0    NIC1    NIC2    NIC3    NIC4    NIC5    NIC6    NIC7    NIC8    NIC9    NIC10   CPU Affinity    NUMA Affinity  GPU NUMA ID
GPU0     X      NV18    NV18    NV18    NV18    NV18    NV18    NV18    PIX     PIX     NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     0-47,96-143     0     N/A
GPU1    NV18     X      NV18    NV18    NV18    NV18    NV18    NV18    PIX     PIX     NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     0-47,96-143     0     N/A
GPU2    NV18    NV18     X      NV18    NV18    NV18    NV18    NV18    NODE    NODE    PIX     PIX     SYS     SYS     SYS     SYS     SYS     SYS     SYS     0-47,96-143     0     N/A
GPU3    NV18    NV18    NV18     X      NV18    NV18    NV18    NV18    NODE    NODE    PIX     PIX     SYS     SYS     SYS     SYS     SYS     SYS     SYS     0-47,96-143     0     N/A
GPU4    NV18    NV18    NV18    NV18     X      NV18    NV18    NV18    SYS     SYS     SYS     SYS     PIX     PIX     NODE    NODE    NODE    NODE    NODE    48-95,144-191   1     N/A
GPU5    NV18    NV18    NV18    NV18    NV18     X      NV18    NV18    SYS     SYS     SYS     SYS     PIX     PIX     NODE    NODE    NODE    NODE    NODE    48-95,144-191   1     N/A
GPU6    NV18    NV18    NV18    NV18    NV18    NV18     X      NV18    SYS     SYS     SYS     SYS     NODE    NODE    PIX     PIX     PIX     NODE    NODE    48-95,144-191   1     N/A
GPU7    NV18    NV18    NV18    NV18    NV18    NV18    NV18     X      SYS     SYS     SYS     SYS     NODE    NODE    PIX     PIX     PIX     NODE    NODE    48-95,144-191   1     N/A
NIC0    PIX     PIX     NODE    NODE    SYS     SYS     SYS     SYS      X      PIX     NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS
NIC1    PIX     PIX     NODE    NODE    SYS     SYS     SYS     SYS     PIX      X      NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS
NIC2    NODE    NODE    PIX     PIX     SYS     SYS     SYS     SYS     NODE    NODE     X      PIX     SYS     SYS     SYS     SYS     SYS     SYS     SYS
NIC3    NODE    NODE    PIX     PIX     SYS     SYS     SYS     SYS     NODE    NODE    PIX      X      SYS     SYS     SYS     SYS     SYS     SYS     SYS
NIC4    SYS     SYS     SYS     SYS     PIX     PIX     NODE    NODE    SYS     SYS     SYS     SYS      X      PIX     NODE    NODE    NODE    NODE    NODE
NIC5    SYS     SYS     SYS     SYS     PIX     PIX     NODE    NODE    SYS     SYS     SYS     SYS     PIX      X      NODE    NODE    NODE    NODE    NODE
NIC6    SYS     SYS     SYS     SYS     NODE    NODE    PIX     PIX     SYS     SYS     SYS     SYS     NODE    NODE     X      PIX     PIX     NODE    NODE
NIC7    SYS     SYS     SYS     SYS     NODE    NODE    PIX     PIX     SYS     SYS     SYS     SYS     NODE    NODE    PIX      X      PIX     NODE    NODE
NIC8    SYS     SYS     SYS     SYS     NODE    NODE    PIX     PIX     SYS     SYS     SYS     SYS     NODE    NODE    PIX     PIX      X      NODE    NODE
NIC9    SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    NODE     X      NODE
NIC10   SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE     X

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
  NIC9: mlx5_11
  NIC10: mlx5_bond_0


ulimit soft: 1024
