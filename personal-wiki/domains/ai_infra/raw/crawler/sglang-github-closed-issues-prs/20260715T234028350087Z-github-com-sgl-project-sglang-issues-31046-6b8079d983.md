---
source_id: sglang-github-closed-issues-prs
title: '[Bug] [Regression] DeepSeek-V4 serving crashes with ValueError: Unrecognized
  configuration class _DeepseekV4ConfigAlias in v0.5.15 (Works in v0.5.14)'
canonical_url: https://github.com/sgl-project/sglang/issues/31046
captured_at: '2026-07-15T23:40:28.350087+00:00'
content_hash: 6b8079d983f38a70de69656464c73229acc75f073dd16d5fd9bcc7fcffaab3c8
---
# [Bug] [Regression] DeepSeek-V4 serving crashes with ValueError: Unrecognized configuration class _DeepseekV4ConfigAlias in v0.5.15 (Works in v0.5.14)

URL: https://github.com/sgl-project/sglang/issues/31046
State: closed
Labels: 
Closed at: 2026-07-15T05:08:21Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

There is a regression in v0.5.15 when serving DeepSeek-V4.

In v0.5.14, the exact same model and command launch successfully and run fine on native SGLang runtime. However, after upgrading to v0.5.15, SGLang incorrectly logs a warning stating "DeepseekV4ForCausalLM has no SGLang implementation" and attempts to fall back to the HF Transformers implementation.

During this fallback path, the internal configuration alias "sglang.srt.utils.hf_transformers.common._DeepseekV4ConfigAlias" is passed to Hugging Face's "AutoModel.from_config", which is not recognized by standard Transformers, resulting in a fatal ValueError and server crash.

### Reproduction

  deepseek-v4-1:
    image: lmsysorg/sglang:v0.5.14-cu129
    volumes:
      - /data/models:/root/.cache/huggingface
    ports:
      - "7002:8000"
    ipc: host
    shm_size: '1024g'
    ulimits:
      memlock: -1
    cap_add:
      - SYS_NICE
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: "all"
              capabilities: [gpu]
    environment:
      - CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
      - SGLANG_DSV4_FP4_EXPERTS=0
    command: >
      sglang serve
        --trust-remote-code
        --enable-cache-report
        --enable-metrics
        --model-path /root/.cache/huggingface/DeepSeek-V4-Flash-FP8
        --tp 8
        --tool-call-parser deepseekv4
        --reasoning-parser deepseek-v4
        --enable-nsa-prefill-context-parallel
        --nsa-prefill-cp-mode round-robin-split
        --speculative-algo EAGLE
        --speculative-num-steps 1
        --speculative-eagle-topk 1
        --speculative-num-draft-tokens 2
        --host 0.0.0.0
        --port 8000

[crashlog.txt](https://github.com/user-attachments/files/29973739/crashlog.txt)

### Environment

Python: 3.12.3 (main, Jun 19 2026, 12:46:00) [GCC 13.3.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA H20-3e
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 12.9, V12.9.86
CUDA Driver Version: 550.163.01
PyTorch: 2.11.0+cu129
sglang: 0.5.15
sglang-kernel: 0.4.4+cu129
flashinfer_python: 0.6.12
flashinfer_cubin: 0.6.12
flashinfer_jit_cache: 0.6.12+cu129
triton: 3.6.0
transformers: 5.12.1
torchao: 0.17.0+cu129
numpy: 2.4.4
aiohttp: 3.14.1
fastapi: 0.139.0
huggingface_hub: 1.23.0
interegular: 0.3.3
modelscope: 1.38.1
orjson: 3.11.9
outlines: 0.1.11
packaging: 26.2
psutil: 7.2.2
pydantic: 2.13.4
python-multipart: 0.0.32
pyzmq: 27.1.0
uvicorn: 0.51.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.2.1
openai: 2.6.1
tiktoken: 0.13.0
anthropic: 0.116.0
litellm: Module Not Found
torchcodec: 0.11.1+cu129
NVIDIA Topology: 
        GPU0    GPU1    GPU2    GPU3    GPU4    GPU5    GPU6    GPU7    NIC0    NIC1    NIC2    NIC3    NIC4    NIC5    NIC6    NIC7    CPU Affinity    NUMA Affinity   GPU NUMA ID
GPU0     X      NV18    NV18    NV18    NV18    NV18    NV18    NV18    PIX     PIX     NODE    NODE    SYS     SYS     SYS     SYS     0-47,96-143     0               N/A
GPU1    NV18     X      NV18    NV18    NV18    NV18    NV18    NV18    NODE    NODE    NODE    NODE    SYS     SYS     SYS     SYS     0-47,96-143     0               N/A
GPU2    NV18    NV18     X      NV18    NV18    NV18    NV18    NV18    NODE    NODE    PIX     PIX     SYS     SYS     SYS     SYS     0-47,96-143     0               N/A
GPU3    NV18    NV18    NV18     X      NV18    NV18    NV18    NV18    NODE    NODE    NODE    NODE    SYS     SYS     SYS     SYS     0-47,96-143     0               N/A
GPU4    NV18    NV18    NV18    NV18     X      NV18    NV18    NV18    SYS     SYS     SYS     SYS     PIX     PIX     NODE    NODE    48-95,144-191   1               N/A
GPU5    NV18    NV18    NV18    NV18    NV18     X      NV18    NV18    SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    48-95,144-191   1               N/A
GPU6    NV18    NV18    NV18    NV18    NV18    NV18     X      NV18    SYS     SYS     SYS     SYS     NODE    NODE    PIX     PIX     48-95,144-191   1               N/A
GPU7    NV18    NV18    NV18    NV18    NV18    NV18    NV18     X      SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    48-95,144-191   1               N/A
NIC0    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS      X      PIX     NODE    NODE    SYS     SYS     SYS     SYS
NIC1    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     PIX      X      NODE    NODE    SYS     SYS     SYS     SYS
NIC2    NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE     X      PIX     SYS     SYS     SYS     SYS
NIC3    NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE    PIX      X      SYS     SYS     SYS     SYS
NIC4    SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS      X      PIX     NODE    NODE
NIC5    SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     PIX      X      NODE    NODE
NIC6    SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE     X      PIX
NIC7    SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE    PIX      X 

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


ulimit soft: 1048576
