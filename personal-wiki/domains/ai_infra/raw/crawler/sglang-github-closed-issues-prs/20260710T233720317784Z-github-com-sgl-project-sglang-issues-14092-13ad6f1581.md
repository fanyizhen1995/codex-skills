---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Error when resume_memory_occupation'
canonical_url: https://github.com/sgl-project/sglang/issues/14092
captured_at: '2026-07-10T23:37:20.317784+00:00'
content_hash: 13ad6f15811209b6fb0a244c248f39e4288c80993fa38d2c0033030fd3e54114
---
# [Bug] Error when resume_memory_occupation

URL: https://github.com/sgl-project/sglang/issues/14092
State: closed
Labels: inactive
Closed at: 2026-07-10T00:39:35Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

When VeRL call `resume_memory_occupation`, the out of memory error occurs:

(SGLangHttpServer pid=250977) [torch_memory_saver.cpp] CUresult error: 2 (out of memory)  file=csrc/utils.h func=cu_mem_create line=194
(WorkerDict pid=209740) WARNING:2025-11-28 16:00:45,396:Async request to resume_memory_occupation timed out (attempt 1)
(SGLangHttpServer pid=250976) [torch_memory_saver.cpp] CUresult error: 2 (out of memory)  file=csrc/utils.h func=cu_mem_create line=194 [repeated 7x across cluster]
(WorkerDict pid=209740) WARNING:2025-11-28 16:01:48,395:Async request to resume_memory_occupation timed out (attempt 2) [repeated 4x across cluster]
(WorkerDict pid=209740) WARNING:2025-11-28 16:02:53,394:Async request to resume_memory_occupation timed out (attempt 3) [repeated 4x across cluster]

Can adding more machines avoid this problem?

### Reproduction

None

### Environment

Python: 3.12.12 | packaged by Anaconda, Inc. | (main, Oct 21 2025, 20:16:04) [GCC 11.2.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA H20
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 12.8, V12.8.61
CUDA Driver Version: 550.144.04
PyTorch: 2.8.0+cu128
sglang: 0.5.5
sgl_kernel: 0.3.16.post5
flashinfer_python: 0.5.0
flashinfer_cubin: 0.5.0
flashinfer_jit_cache: Module Not Found
triton: 3.4.0
transformers: 4.57.1
torchao: 0.9.0
numpy: 2.2.6
aiohttp: 3.13.2
fastapi: 0.121.1
hf_transfer: 0.1.9
huggingface_hub: 0.36.0
interegular: 0.3.3
modelscope: 1.31.0
orjson: 3.11.4
outlines: 0.1.11
packaging: 25.0
psutil: 7.1.3
pydantic: 2.12.4
python-multipart: 0.0.20
pyzmq: 27.1.0
uvicorn: 0.38.0
uvloop: 0.22.1
vllm: 0.11.0
xgrammar: 0.1.25
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.72.0
litellm: Module Not Found
decord2: 2.0.0
NVIDIA Topology: 
        GPU0    GPU1    GPU2    GPU3    GPU4    GPU5    GPU6    GPU7    NIC0    NIC1    NIC2    NIC3    NIC4    NIC5    NIC6    NIC7    NIC8    NIC9    NIC10   NIC11   NIC12       NIC13   NIC14   NIC15   NIC16   NIC17   NIC18   NIC19   NIC20   NIC21   NIC22   NIC23   NIC24   NIC25   NIC26   NIC27   NIC28   NIC29   NIC30   NIC31   NIC32   NIC33       NIC34   NIC35   CPU Affinity    NUMA Affinity   GPU NUMA ID
GPU0     X      NV18    NV18    NV18    NV18    NV18    NV18    NV18    PIX     PIX     PIX     PIX     PIX     PIX     PIX     PIX     NODE    NODE    NODE    NODE    NODENODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     NODEPIX     0-55,112-167    0               N/A
GPU1    NV18     X      NV18    NV18    NV18    NV18    NV18    NV18    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODENODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     NODENODE    0-55,112-167    0               N/A
GPU2    NV18    NV18     X      NV18    NV18    NV18    NV18    NV18    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     PIX     PIX     PIX     PIXPIX      PIX     PIX     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     PIXNODE     0-55,112-167    0               N/A
GPU3    NV18    NV18    NV18     X      NV18    NV18    NV18    NV18    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODENODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     NODENODE    0-55,112-167    0               N/A
GPU4    NV18    NV18    NV18    NV18     X      NV18    NV18    NV18    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     PIX     PIX     PIX     PIX     PIX     PIX     PIX     PIX     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     NODE    SYSSYS      70-99,102-107   1               N/A
GPU5    NV18    NV18    NV18    NV18    NV18     X      NV18    NV18    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    SYSSYS      70-99,102-107   1               N/A
GPU6    NV18    NV18    NV18    NV18    NV18    NV18     X      NV18    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     PIX     PIX     PIX     PIX     PIX     PIX     PIX     NODE    PIX     SYSSYS      70-99,102-107   1               N/A
GPU7    NV18    NV18    NV18    NV18    NV18    NV18    NV18     X      SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    SYSSYS      70-99,102-107   1               N/A
NIC0    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS      X      PIX     PIX     PIX     PIX     PIX     PIX     PIX     NODE    NODE    NODE    NODE    NODENODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     NODEPIX
NIC1    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     PIX      X      PIX     PIX     PIX     PIX     PIX     PIX     NODE    NODE    NODE    NODE    NODENODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     NODEPIX
NIC2    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     PIX     PIX      X      PIX     PIX     PIX     PIX     PIX     NODE    NODE    NODE    NODE    NODENODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     NODEPIX
NIC3    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     PIX     PIX     PIX      X      PIX     PIX     PIX     PIX     NODE    NODE    NODE    NODE    NODENODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     NODEPIX
NIC4    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     PIX     PIX     PIX     PIX      X      PIX     PIX     PIX     NODE    NODE    NODE    NODE    NODENODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     NODEPIX
NIC5    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     PIX     PIX     PIX     PIX     PIX      X      PIX     PIX     NODE    NODE    NODE    NODE    NODENODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     NODEPIX
NIC6    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     PIX     PIX     PIX     PIX     PIX     PIX      X      PIX     NODE    NODE    NODE    NODE    NODENODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     NODEPIX
NIC7    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     PIX     PIX     PIX     PIX     PIX     PIX     PIX      X      NODE    NODE    NODE    NODE    NODENODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     NODEPIX
NIC8    NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE     X      PIX     PIX     PIX     PIXPIX      PIX     PIX     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     PIXNODE
NIC9    NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX      X      PIX     PIX     PIXPIX      PIX     PIX     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     PIXNODE
NIC10   NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     PIX      X      PIX     PIXPIX      PIX     PIX     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     PIXNODE
NIC11   NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     PIX     PIX      X      PIXPIX      PIX     PIX     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     PIXNODE
NIC12   NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     PIX     PIX     PIX      X PIX      PIX     PIX     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     PIXNODE
NIC13   NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     PIX     PIX     PIX     PIX X       PIX     PIX     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     PIXNODE
NIC14   NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     PIX     PIX     PIX     PIXPIX       X      PIX     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     PIXNODE
NIC15   NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     PIX     PIX     PIX     PIXPIX      PIX      X      SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     PIXNODE
NIC16   SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS      X      PIX     PIX     PIX     PIX     PIX     PIX     PIX     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     NODE    SYSSYS
NIC17   SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     PIX      X      PIX     PIX     PIX     PIX     PIX     PIX     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     NODE    SYSSYS
NIC18   SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     PIX     PIX      X      PIX     PIX     PIX     PIX     PIX     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     NODE    SYSSYS
NIC19   SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     PIX     PIX     PIX      X      PIX     PIX     PIX     PIX     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     NODE    SYSSYS
NIC20   SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     PIX     PIX     PIX     PIX      X      PIX     PIX     PIX     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     NODE    SYSSYS
NIC21   SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     PIX     PIX     PIX     PIX     PIX      X      PIX     PIX     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     NODE    SYSSYS
NIC22   SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     PIX     PIX     PIX     PIX     PIX     PIX      X      PIX     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     NODE    SYSSYS
NIC23   SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     PIX     PIX     PIX     PIX     PIX     PIX     PIX      X      NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     NODE    SYSSYS
NIC24   SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE     X      PIX     PIX     PIX     PIX     PIX     PIX     PIX     NODE    PIX     SYSSYS
NIC25   SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX      X      PIX     PIX     PIX     PIX     PIX     PIX     NODE    PIX     SYSSYS
NIC26   SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     PIX      X      PIX     PIX     PIX     PIX     PIX     NODE    PIX     SYSSYS
NIC27   SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     PIX     PIX      X      PIX     PIX     PIX     PIX     NODE    PIX     SYSSYS
NIC28   SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     PIX     PIX     PIX      X      PIX     PIX     PIX     NODE    PIX     SYSSYS
NIC29   SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     PIX     PIX     PIX     PIX      X      PIX     PIX     NODE    PIX     SYSSYS
NIC30   SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     PIX     PIX     PIX     PIX     PIX      X      PIX     NODE    PIX     SYSSYS
NIC31   SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     PIX     PIX     PIX     PIX     PIX     PIX      X      NODE    PIX     SYSSYS
NIC32   SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     PIX     PIX     PIX     PIX     PIX     PIX     PIX     PIX     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE     X      NODE    SYSSYS
NIC33   SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYSSYS      SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     PIX     PIX     PIX     PIX     PIX     PIX     PIX     NODE     X      SYSSYS
NIC34   NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    NODE    NODE    NODE    NODE    PIX     PIX     PIX     PIX     PIXPIX      PIX     PIX     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS      X NODE
NIC35   PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     PIX     PIX     PIX     PIX     PIX     PIX     PIX     PIX     NODE    NODE    NODE    NODE    NODENODE    NODE    NODE    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     NODE X 

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
  NIC11: mlx5_11
  NIC12: mlx5_12
  NIC13: mlx5_13
  NIC14: mlx5_14
  NIC15: mlx5_15
  NIC16: mlx5_16
  NIC17: mlx5_17
  NIC18: mlx5_18
  NIC19: mlx5_19
  NIC20: mlx5_20
  NIC21: mlx5_21
  NIC22: mlx5_22
  NIC23: mlx5_23
  NIC24: mlx5_24
  NIC25: mlx5_25
  NIC26: mlx5_26
  NIC27: mlx5_27
  NIC28: mlx5_28
  NIC29: mlx5_29
  NIC30: mlx5_30
  NIC31: mlx5_31
  NIC32: mlx5_bond_0
  NIC33: mlx5_bond_1
  NIC34: mlx5_bond_2
  NIC35: mlx5_bond_3


ulimit soft: 655350
