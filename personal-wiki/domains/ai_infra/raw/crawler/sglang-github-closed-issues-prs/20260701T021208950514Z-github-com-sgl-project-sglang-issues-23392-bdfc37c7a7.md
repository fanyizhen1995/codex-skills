---
source_id: sglang-github-closed-issues-prs
title: '[Bug] shared-prefix load corrupts unrelated requests in SGLang speculative
  decoding'
canonical_url: https://github.com/sgl-project/sglang/issues/23392
captured_at: '2026-07-01T02:12:08.950514+00:00'
content_hash: bdfc37c7a722214454bf0d2ddba16046eaeec17a6968425b1cb118a05bb60f2b
---
# [Bug] shared-prefix load corrupts unrelated requests in SGLang speculative decoding

URL: https://github.com/sgl-project/sglang/issues/23392
State: closed
Labels: inactive
Closed at: 2026-06-30T00:48:52Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

## Summary

We found a reproducible KV/cache corruption bug in **SGLang 0.5.10.post1** triggered by concurrent shared-prefix requests plus mid-flight cancellation and retry.

We will show the cleanist case we found, which confirms **15/15** runs with:

- `temperature=0` with --enable-deterministic-inference enabled
- shared prefix requests (`prefix_len=128`)
- concurrent cancels at `15ms` and `19ms`
- retries of the cancelled requests
- unrelated concurrent requests arriving in the same window

The corrupted output is not limited to the retried requests. At least one unrelated concurrent request is also corrupted, which suggests **shared cache state is being reused or released incorrectly after cancellation**.

## Why this is different from #22819
Earlier I filed #22819, but this bug seems different, the trigger shape is different:

- `#22819`:
  - block-boundary corruption around `prefix_len == 64`
  - reproduced with `--enable-deterministic-inference`
  - no cancel/retry required
  - current fix discussion is about unfinished cache insertion / `cache_unfinished_req`

- This issue:
  - concurrent shared-prefix burst with `prefix_len = 128`
  - two requests are cancelled while in flight, then retried
  - corruption spreads to unrelated concurrent requests
  - reproduced under speculative decoding with `--speculative-algorithm NGRAM`

So this does not look like the same boundary-only scenario. It appears to be a cancel-path cache corruption bug that can poison later requests in the same concurrent window.



### Reproduction

Qucik explanation of the trace: 
Trace shape:

1. Three `scn_family` requests start with the same prefix:
   - `scn_0` at `0ms`
   - `scn_1` at `5ms`
   - `scn_2` at `10ms`
   - all use `prompt_len=512`, `max_tokens=12`, `prefix_len=128`, `temperature=0`
2. Cancel:
   - `scn_0` at `15ms`
   - `scn_1` at `19ms`
3. Retry / concurrent interference:
   - `scn_0_retry` at `23ms`
   - four unrelated requests arrive at `24-29ms`
   - `scn_1_retry` at `104ms`

To reproduce:

```bash
python3 -m sglang.launch_server \
    --model-path Qwen/Qwen2.5-0.5B-Instruct \
    --context-length 32768 \
    --speculative-algorithm NGRAM \
    --speculative-num-draft-tokens 5
```

We baked in the finding in this script: [repro.py](https://gist.github.com/Yunzez/7dedd70360e9d2fdec76d72aa15b84fd#file-repro-py)

```bash
python3 repro.py \
    --base-url http://localhost:30000 \
    --runs 15
```

### Environment

check_env
Python: 3.12.3 (main, Mar 3 2026, 12:15:18) [GCC 13.3.0]
CUDA available: True
GPU 0: NVIDIA RTX A6000
GPU 0 Compute Capability: 8.6
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 12.9, V12.9.86
CUDA Driver Version: 590.48.01
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
�[4mGPU0 NIC0 NIC1 NIC2 CPU Affinity NUMA Affinity GPU NUMA ID�[0m
GPU0 X NODE NODE SYS 16-31 1 N/A
NIC0 NODE X PIX SYS
NIC1 NODE PIX X SYS
NIC2 SYS SYS SYS X

Legend:

X = Self
SYS = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
PHB = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)
PXB = Connection traversing multiple PCIe bridges (without traversing the PCIe Host Bridge)
PIX = Connection traversing at most a single PCIe bridge
NV# = Connection traversing a bonded set of # NVLinks

NIC Legend:

NIC0: mlx5_2
NIC1: mlx5_3
NIC2: mlx5_bond_0

ulimit soft: 1024
