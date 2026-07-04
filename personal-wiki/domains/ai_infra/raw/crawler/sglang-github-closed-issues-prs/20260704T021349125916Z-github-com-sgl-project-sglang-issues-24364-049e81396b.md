---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Qwen3.6 hybrid Mamba: Mamba pool 9-18 GiB allocation OOM on RTX PRO
  6000 Blackwell + WSL2'
canonical_url: https://github.com/sgl-project/sglang/issues/24364
captured_at: '2026-07-04T02:13:49.125916+00:00'
content_hash: 049e81396bf26d5e950d8f748b45767b0d5208b0a7d2fccafb83b04f1ec6b892
---
# [Bug] Qwen3.6 hybrid Mamba: Mamba pool 9-18 GiB allocation OOM on RTX PRO 6000 Blackwell + WSL2

URL: https://github.com/sgl-project/sglang/issues/24364
State: closed
Labels: inactive
Closed at: 2026-07-04T00:38:26Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

SGLang 0.5.10.post1 cannot load **Qwen3.6 hybrid Mamba models** (Qwen3_5ForConditionalGeneration / Qwen3_5MoeForConditionalGeneration) on **RTX PRO 6000 Blackwell** (96 GB VRAM, sm_120) under **WSL2 Ubuntu 22.04**.

Mamba pool allocation fails with `torch.OutOfMemoryError: Tried to allocate 9-18 GiB` even though 50+ GiB of VRAM is free, because of ~16 GiB hidden non-PyTorch CUDA overhead specific to WSL2 + Blackwell.

**Cross-reference:** Same root cause as vllm-project/vllm#41619 — both vLLM and SGLang affected because both use PyTorch CUDA allocator on the same hardware/OS.

## Error
File "/home/nomugop/sglang-env/lib/python3.10/site-packages/sglang/srt/mem_cache/memory_pool.py",
line 499, in _init_mamba_pool
torch.OutOfMemoryError: CUDA out of memory.
Tried to allocate 18.56 GiB.
GPU 0 has a total capacity of 95.59 GiB of which 53.44 GiB is free.
this process has 17179869184.00 GiB memory in use   ← display bug, actually 16 GiB
Of the allocated memory 39.43 GiB is allocated by PyTorch
sglang.service: Main process exited, code=killed, status=9/KILL
The "non-PyTorch memory: 16 GiB" is abnormally high (typical native Linux: 1-2 GiB). This is WSL2 GPU passthrough overhead on Blackwell sm_120.

Profiler logs before OOM:
[Init] Detected fp8 checkpoint
[Load weight end] mem usage=39.09 GB, avail mem=53.87 GB
[Init] Disabling overlap schedule since mamba no_buffer is not compatible with overlap schedule

## What I tried (none help)

- `--mem-fraction-static`: 0.70/0.85/0.90/0.95 — all OOM (or sglang's own "Not enough memory" check)
- `--mamba-full-memory-ratio`: 0.05/0.1/0.3/0.9 — all OOM
- `--max-mamba-cache-size`: 256/512 — does not help
- `--max-running-requests`: 1/16 — same OOM
- `--context-length`: 2048/4096/8192/16384 — same OOM
- `--max-total-tokens 4096` — does not help
- `--disable-cuda-graph` / `--disable-radix-cache` — does not help
- NVIDIA driver 596.36 → 581.80 RTX Enterprise (full DDU clean install) — same overhead
- vLLM 0.20.0 / 0.17.1 with same hardware — same problem (filed at vllm-project/vllm#41619)

Also tested **Qwen/Qwen3.6-35B-A3B-FP8** (MoE) — fails with `Tried to allocate 4.99 GiB` for Mamba state. All 4 Qwen3.6 models on disk fail.

## SGLang-specific warnings during init (might be related)
Failed to get device capability: SM 12.x requires CUDA >= 12.9.
DeepGemm is enabled but the scale_fmt of checkpoint is not ue8m0.
This might cause accuracy degradation on Blackwell.


Have CUDA 12.8, not 12.9 — but bumping CUDA may not be root cause since vLLM with CUDA 13 has identical OOM pattern.

## Hypothesis

WSL2 Blackwell hidden ~16 GiB CUDA overhead is not visible to `torch.cuda.mem_get_info()`. SGLang's `_resolve_memory_pool_config` and `_init_mamba_pool` use this for sizing → planned Mamba pool is too big for actual contiguous free memory.

## Suggested fixes

1. Subtract observed "non-PyTorch memory" from available memory in mem_pool sizing
2. Allow Mamba pool allocation in chunks instead of single contiguous tensor
3. Add `--mamba-pool-chunk-size N` flag for manual control

## Workarounds (none ideal)

None working for SGLang. Currently using non-Mamba models (Qwen3-32B-AWQ) on vLLM as workaround.

Happy to test patches or provide more debug data.


### Reproduction

HF_HUB_OFFLINE=1 python -m sglang.launch_server \
  --model-path Qwen/Qwen3.6-27B-FP8 \
  --host 0.0.0.0 --port 8000 \
  --mem-fraction-static 0.85 \
  --max-running-requests 16 \
  --context-length 16384 \
  --dtype bfloat16 \
  --trust-remote-code \
  --disable-cuda-graph
Model: Qwen/Qwen3.6-27B-FP8 (Qwen3_5ForConditionalGeneration arch)



### Environment

Failed to get device capability: SM 12.x requires CUDA >= 12.9.
Failed to get device capability: SM 12.x requires CUDA >= 12.9.
Python: 3.10.12 (main, Mar  3 2026, 11:56:32) [GCC 11.4.0]
CUDA available: True
GPU 0: NVIDIA RTX PRO 6000 Blackwell Workstation Edition
GPU 0 Compute Capability: 12.0
CUDA_HOME: None
PyTorch: 2.9.1+cu128
sglang: 0.5.10.post1
sglang-kernel: 0.4.1
flashinfer_python: 0.6.7.post3
flashinfer_cubin: 0.6.7.post3
flashinfer_jit_cache: Module Not Found
triton: 3.5.1
transformers: 5.3.0
torchao: 0.9.0
numpy: 2.2.6
aiohttp: 3.13.5
fastapi: 0.136.1
huggingface_hub: 1.13.0
interegular: 0.3.3
modelscope: 1.36.3
orjson: 3.11.8
outlines: 0.1.11
packaging: 26.2
psutil: 7.2.2
pydantic: 2.13.3
python-multipart: 0.0.27
pyzmq: 27.1.0
uvicorn: 0.46.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.1.32
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.97.0
litellm: Module Not Found
torchcodec: 0.9.1+cu128
NVIDIA Topology: 
	[4mGPU0	CPU Affinity	NUMA Affinity	GPU NUMA ID[0m
GPU0	 X 				N/A

Legend:

  X    = Self
  SYS  = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
  NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
  PHB  = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)
  PXB  = Connection traversing multiple PCIe bridges (without traversing the PCIe Host Bridge)
  PIX  = Connection traversing at most a single PCIe bridge
  NV#  = Connection traversing a bonded set of # NVLinks

Hypervisor vendor:: Microsoft
ulimit soft: 10240
