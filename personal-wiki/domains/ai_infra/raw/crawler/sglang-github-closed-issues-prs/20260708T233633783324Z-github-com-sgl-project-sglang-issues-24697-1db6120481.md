---
source_id: sglang-github-closed-issues-prs
title: '[Bug] sleep mode crashes with cudaErrorIllegalAddress when DFlash speculative
  decoding + CPU weight backup are enabled'
canonical_url: https://github.com/sgl-project/sglang/issues/24697
captured_at: '2026-07-08T23:36:33.783324+00:00'
content_hash: 1db6120481f991e03464dc15ab1a0cb5a76d3eab8510ce22e7d1fb755e7a5586
---
# [Bug] sleep mode crashes with cudaErrorIllegalAddress when DFlash speculative decoding + CPU weight backup are enabled

URL: https://github.com/sgl-project/sglang/issues/24697
State: closed
Labels: inactive
Closed at: 2026-07-08T00:34:34Z
Merged at: 

### Checklist

- [ ] I searched related issues but found no solution.
- [ ] The bug persists in the latest version.
- [ ] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [ ] Please use English. Otherwise, it will be closed.

### Describe the bug

### Describe the bug

When using SGLang v0.5.1.1 with **sleep mode** (`--enable-memory-saver`) combined with **DFlash speculative decoding** and **CPU weight backup** (`--enable-weights-cpu-backup`, `--enable-draft-weights-cpu-backup`), triggering sleep mode causes a fatal `CUDA error: an illegal memory access was encountered` (cudaErrorIllegalAddress).

The error is followed by `SIGQUIT` indicating child process failure, making sleep mode completely unusable in this configuration.

This is critical for our use case as we need to switch between training and inference on the same GPU.



### Reproduction

uv run sglang serve \
  --model-path /home/xxx/models/fp8 \
  --quantization fp8 \
  --trust-remote-code \
  --attention-backend flashinfer \
  --context-length 260000 \
  --dtype auto \
  --max-running-requests 12 \
  --chunked-prefill-size 12288 \
  --enable-dynamic-chunking \
  --kv-cache-dtype auto \
  --tp-size 1 \
  --host 127.0.0.1 \
  --mamba-scheduler-strategy extra_buffer \
  --reasoning-parser qwen3 \
  --tool-call-parser qwen3_coder \
  --allow-auto-truncate \
  --speculative-algorithm DFLASH \
  --speculative-draft-model-path /home/xxx/models/dflash \
  --speculative-num-draft-tokens 16 \
  --port 1234 \
  --max-prefill-tokens 65536 \
  --enable-memory-saver \
  --enable-weights-cpu-backup \
  --enable-draft-weights-cpu-backup \
  --mem-fraction-static 0.8

### Environment

Python: 3.11.15 (main, Apr  7 2026, 20:48:58) [Clang 22.1.1 ]
CUDA available: True
GPU 0: NVIDIA RTX PRO 6000 Blackwell Workstation Edition
GPU 0 Compute Capability: 12.0
CUDA_HOME: /usr/local/cuda-13.2
NVCC: Cuda compilation tools, release 13.2, V13.2.78
CUDA Driver Version: 595.58.03
PyTorch: 2.11.0+cu130
sglang: 0.5.11
sglang-kernel: 0.4.2
flashinfer_python: 0.6.8.post1
flashinfer_cubin: 0.6.8.post1
flashinfer_jit_cache: Module Not Found
triton: 3.6.0
transformers: 5.6.0
torchao: 0.17.0
numpy: 2.3.5
aiohttp: 3.13.5
fastapi: 0.136.1
huggingface_hub: 1.14.0
interegular: 0.3.3
modelscope: 1.36.3
orjson: 3.11.9
outlines: 0.1.11
packaging: 26.2
psutil: 7.2.2
pydantic: 2.13.4
python-multipart: 0.0.27
pyzmq: 27.1.0
uvicorn: 0.46.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.1.32
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.100.0
litellm: Module Not Found
torchcodec: 0.11.1
NVIDIA Topology: 
	GPU0	CPU Affinity	NUMA Affinity	GPU NUMA ID
GPU0	 X 	0-27	0		N/A

Legend:

  X    = Self
  SYS  = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
  NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
  PHB  = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)
  PXB  = Connection traversing multiple PCIe bridges (without traversing the PCIe Host Bridge)
  PIX  = Connection traversing at most a single PCIe bridge
  NV#  = Connection traversing a bonded set of # NVLinks

ulimit soft: 1024
