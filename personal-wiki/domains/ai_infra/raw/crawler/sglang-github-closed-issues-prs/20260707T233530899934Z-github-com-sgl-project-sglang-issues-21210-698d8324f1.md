---
source_id: sglang-github-closed-issues-prs
title: '[Bug]  EAGLE draft_forward leaks padded state across decode steps under DP
  attention, causing negative-dimension crash'
canonical_url: https://github.com/sgl-project/sglang/issues/21210
captured_at: '2026-07-07T23:35:30.899934+00:00'
content_hash: 698d8324f18d69495855424da40f7ed452ee4b736b45d1b47d94f62f6e918b7f
---
# [Bug]  EAGLE draft_forward leaks padded state across decode steps under DP attention, causing negative-dimension crash

URL: https://github.com/sgl-project/sglang/issues/21210
State: closed
Labels: inactive
Closed at: 2026-05-23T00:45:34Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

 ## Summary

  Under EAGLE speculative decoding, `draft_forward()` performs multiple decode-mode forwards on the same
  `forward_batch`. When DP attention is enabled and padding is introduced by MLP sync, some padded state is not restored
  after a decode step.

  As a result, the next speculative step may re-enter `prepare_mlp_sync_batch()` with stale padded metadata and
  eventually crash with:

  ```text
  RuntimeError: Trying to create tensor with negative dimension -1: [-1]

  This kills the SGLang worker and can further cause router retry failures, health check failures, and training hangs.
 ```

<img width="899" height="372" alt="Image" src="https://github.com/user-attachments/assets/46b5f634-2e83-447c-855b-982b3a2bfe03" />

I will open a PR with a minimal fix for this issue. #21207 

### Reproduction

python3 -m sglang.launch_server \
    --model-path /gfs/space/chatrl/public/models/ZhipuAI/GLM-4.7-Flash-0309 \
    --trust-remote-code \
    --tp-size 8 \
    --dp-size 4 \
    --enable-dp-attention \
    --enable-dp-lm-head \
    --speculative-algorithm EAGLE \
    --speculative-num-steps 2 \
    --speculative-eagle-topk 1 \
    --speculative-num-draft-tokens 3 \
    --moe-dense-tp-size 1 \
    --mem-fraction-static 0.7 \
    --max-running-requests 512


 This issue requires all of the following:
  - EAGLE speculative decoding
      - --speculative-algorithm EAGLE
      - --speculative-num-steps >= 2
  - MoE model
  - DP attention enabled
  - attn_tp_size > 1
      - e.g. tp_size=8, dp_size=4 -> attn_tp_size=2
  - A batch shape that causes ceil_align(num_tokens, attn_tp_size) to insert padding

  ## Minimal Repro

  Example setup that hit this in production:

  - GLM-4.7-Flash MoE
  - tp_size=8
  - dp_size=4
  - --enable-dp-attention
  - --speculative-algorithm EAGLE
  - --speculative-num-steps 2

### Environment

root@6a3654c51622592b9b2d4f8f62f268b4-taskrole1-0:/gfs/platform/public/infra/lxr/sglang# python3 -m sglang.check_env
Python: 3.12.3 (main, Jan 22 2026, 20:57:42) [GCC 13.3.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA H800 80GB
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 12.9, V12.9.86
CUDA Driver Version: 580.105.08
PyTorch: 2.9.1+cu129
sglang: 0.5.9
sgl_kernel: 0.3.21
flashinfer_python: 0.6.3
flashinfer_cubin: 0.6.3
flashinfer_jit_cache: 0.6.3+cu129
triton: 3.5.1
transformers: 5.3.0
torchao: 0.9.0
numpy: 1.26.4
aiohttp: 3.13.3
fastapi: 0.131.0
hf_transfer: 0.1.9
huggingface_hub: 1.7.2
interegular: 0.3.3
modelscope: 1.34.0
orjson: 3.11.7
outlines: 0.1.11
packaging: 26.0
psutil: 7.2.2
pydantic: 2.12.5
python-multipart: 0.0.22
pyzmq: 27.1.0
uvicorn: 0.41.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.1.27
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.83.0
litellm: Module Not Found
decord2: 3.0.0
NVIDIA Topology: 
        GPU0    GPU1    GPU2    GPU3    GPU4    GPU5    GPU6    GPU7    NIC0    NIC1    NIC2    NIC3    NIC4    NIC5    NIC6    NIC7    NIC8    NIC9    CPU Affinity       NUMA Affinity   GPU NUMA ID
GPU0     X      NV18    NV18    NV18    NV18    NV18    NV18    NV18    SYS     PIX     PXB     PXB     PXB     SYS     SYS     SYS     SYS     PXB     0-45,92-1370               N/A
GPU1    NV18     X      NV18    NV18    NV18    NV18    NV18    NV18    SYS     PXB     PIX     PXB     PXB     SYS     SYS     SYS     SYS     PXB     0-45,92-1370               N/A
GPU2    NV18    NV18     X      NV18    NV18    NV18    NV18    NV18    SYS     PXB     PXB     PIX     PXB     SYS     SYS     SYS     SYS     PXB     0-45,92-1370               N/A
GPU3    NV18    NV18    NV18     X      NV18    NV18    NV18    NV18    SYS     PXB     PXB     PXB     PIX     SYS     SYS     SYS     SYS     PXB     0-45,92-1370               N/A
GPU4    NV18    NV18    NV18    NV18     X      NV18    NV18    NV18    SYS     SYS     SYS     SYS     SYS     PIX     PXB     PXB     PXB     SYS     46-91,138-183      1               N/A
GPU5    NV18    NV18    NV18    NV18    NV18     X      NV18    NV18    SYS     SYS     SYS     SYS     SYS     PXB     PIX     PXB     PXB     SYS     46-91,138-183      1               N/A
GPU6    NV18    NV18    NV18    NV18    NV18    NV18     X      NV18    SYS     SYS     SYS     SYS     SYS     PXB     PXB     PIX     PXB     SYS     46-91,138-183      1               N/A
GPU7    NV18    NV18    NV18    NV18    NV18    NV18    NV18     X      SYS     SYS     SYS     SYS     SYS     PXB     PXB     PXB     PIX     SYS     46-91,138-183      1               N/A
NIC0    SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS      X      SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS     SYS
NIC1    PIX     PXB     PXB     PXB     SYS     SYS     SYS     SYS     SYS      X      PXB     PXB     PXB     SYS     SYS     SYS     SYS     PXB
NIC2    PXB     PIX     PXB     PXB     SYS     SYS     SYS     SYS     SYS     PXB      X      PXB     PXB     SYS     SYS     SYS     SYS     PXB
NIC3    PXB     PXB     PIX     PXB     SYS     SYS     SYS     SYS     SYS     PXB     PXB      X      PXB     SYS     SYS     SYS     SYS     PXB
NIC4    PXB     PXB     PXB     PIX     SYS     SYS     SYS     SYS     SYS     PXB     PXB     PXB      X      SYS     SYS     SYS     SYS     PXB
NIC5    SYS     SYS     SYS     SYS     PIX     PXB     PXB     PXB     SYS     SYS     SYS     SYS     SYS      X      PXB     PXB     PXB     SYS
NIC6    SYS     SYS     SYS     SYS     PXB     PIX     PXB     PXB     SYS     SYS     SYS     SYS     SYS     PXB      X      PXB     PXB     SYS
NIC7    SYS     SYS     SYS     SYS     PXB     PXB     PIX     PXB     SYS     SYS     SYS     SYS     SYS     PXB     PXB      X      PXB     SYS
NIC8    SYS     SYS     SYS     SYS     PXB     PXB     PXB     PIX     SYS     SYS     SYS     SYS     SYS     PXB     PXB     PXB      X      SYS
NIC9    PXB     PXB     PXB     PXB     SYS     SYS     SYS     SYS     SYS     PXB     PXB     PXB     PXB     SYS     SYS     SYS     SYS      X 

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
  NIC1: mlx5_gdr_0
  NIC2: mlx5_gdr_1
  NIC3: mlx5_gdr_2
  NIC4: mlx5_gdr_3
  NIC5: mlx5_gdr_4
  NIC6: mlx5_gdr_5
  NIC7: mlx5_gdr_6
  NIC8: mlx5_gdr_7
  NIC9: mlx5_stor_0


ulimit soft: 1048576
