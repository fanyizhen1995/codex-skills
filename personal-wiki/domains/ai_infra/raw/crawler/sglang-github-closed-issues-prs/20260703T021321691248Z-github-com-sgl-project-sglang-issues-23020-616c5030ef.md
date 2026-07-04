---
source_id: sglang-github-closed-issues-prs
title: '[Bug] PD Disaggregation: Gradual KV cache corruption causes model output to
  degenerate into gibberish after ~100 requests'
canonical_url: https://github.com/sgl-project/sglang/issues/23020
captured_at: '2026-07-03T02:13:21.691248+00:00'
content_hash: 616c5030ef51c5b0c52f09e03a230cac543aa3cd5066528ddb9c3d84859d4b4b
---
# [Bug] PD Disaggregation: Gradual KV cache corruption causes model output to degenerate into gibberish after ~100 requests

URL: https://github.com/sgl-project/sglang/issues/23020
State: closed
Labels: 
Closed at: 2026-04-22T09:04:44Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

## Summary

We are serving **GLM-5.1 (744B MoE)** using SGLang's **PD (Prefill-Decode) disaggregation** mode with **Mooncake transfer engine**. Our setup uses heterogeneous GPUs: 4 nodes of 8×RTX 5090 as prefill workers (PP4 TP8) and 1 node of 8×H20 as the decode worker (TP8 DP8). KV cache is transferred from prefill to decode via Mooncake (RDMA or TCP).

We evaluated accuracy using **GPQA Diamond** — a 198-question graduate-level science benchmark that requires long-chain reasoning (each question generates 5K–60K+ thinking tokens). We discovered that **model output quality degrades progressively as more requests are processed**:

- **Requests 1–50**: 94–96% accuracy (matches standalone)
- **Requests 51–100**: 68–84% accuracy (noticeable drop)
- **Requests 101–150**: 46–55% accuracy (severe degradation)
- **Requests 151+**: 25–41% accuracy (near random guessing, 4-choice = 25% baseline)

Inspecting the actual outputs from the degraded state reveals the model is **not simply choosing wrong answers** — it produces **repetitive gibberish, Unicode garbage, and infinite loops** (examples below), which is characteristic of **corrupted KV cache data** causing the attention mechanism to lock into degenerate states.

**The issue does not occur in standalone mode.** Running the same FP8 model on the same H20 hardware without PD disaggregation achieves **85.3% accuracy that remains stable throughout all 198 questions**. Restarting the PD system recovers accuracy — questions that were wrong in the degraded state become correct again on a fresh restart (15/22 = 68% recovery rate).

We tested **7 different PD configurations** (RDMA vs TCP, with/without EAGLE, with/without overlap scheduling, FP8 vs NVFP4) and **all show the same degradation pattern**, ruling out transport-layer, speculative decoding, and quantization as root causes. The issue appears to be in SGLang's PD disaggregation framework itself.

**Note**: Short-output benchmarks are unaffected — MMLU (0.879) and GSM8K (0.949) both score normally in PD mode, matching standalone results. The issue only manifests with **long reasoning chains** (thousands of thinking tokens per request), suggesting the corruption scales with KV transfer size or decode duration.

## Environment

- **SGLang version**: Latest main branch (commit from ~April 2026)
- **P nodes (Prefill)**: 4×8 RTX 5090 32GB (SM120), PP4 TP8, Mooncake with CPU bounce buffer RDMA
- **D node (Decode)**: 1×8 H20 141GB (SM90), TP8 DP8, Mooncake with GPUDirect RDMA
- **Model**: GLM-5.1 744B MoE (FP8 and NVFP4 variants tested)
- **KV cache dtype**: bfloat16 on both sides
- **Benchmark**: GPQA Diamond (198 graduate-level science questions requiring long-chain reasoning, 5K-60K+ thinking tokens)

## Reproduction

### Standalone (no degradation)
```bash
# D node standalone — accuracy stable throughout
sglang serve --model-path /models/GLM-5.1-FP8 --tp 8 --dp 8 --enable-dp-attention \
  --kv-cache-dtype bfloat16 --speculative-algorithm EAGLE ...
# Result: 168/197 = 85.3%, stable across all segments
```

### PD Disaggregation (degradation)
```bash
# P node (prefill)
python3 -m sglang.launch_server --model-path /models/GLM-5.1-FP8 \
  --nnodes 4 --node-rank $RANK --tp 8 --pp-size 4 \
  --kv-cache-dtype bfloat16 --disaggregation-mode prefill \
  --disaggregation-transfer-backend mooncake ...

# D node (decode)
sglang serve --model-path /models/GLM-5.1-FP8 --tp 8 --dp 8 --enable-dp-attention \
  --kv-cache-dtype bfloat16 --speculative-algorithm EAGLE \
  --disaggregation-mode decode --disaggregation-transfer-backend mooncake ...
```

## Experimental Data

### Accuracy by question range (50-question segments)

| Configuration | 1-50 | 51-100 | 101-150 | 151+ | Overall |
|---|---|---|---|---|---|
| FP8 standalone (H20) | 94% | 90% | 86% | 70% | **85.3%** |
| W4A16 standalone (H20) | 94% | 92% | 86% | 75% | **86.9%** |
| FP8+FP8 PD (RDMA bounce) | 96% | 74% | 55% | — | **77.4%** (133q) |
| FP8+FP8 PD (TCP) | 94% | 84% | 46% | — | **84.1%** (113q) |
| FP8+FP8 PD (no overlap) | 96% | 66% | — | — | **81.4%** (97q) |
| FP8+FP8 PD (no EAGLE) | 96% | 68% | 48% | 41% | **66.9%** (172q) |
| NVFP4+NVFP4 PD (RDMA) | 90% | 80% | 74% | 83% | **81.6%** (190q) |

### Key observations

1. **All PD configurations degrade** — the first 50 questions are comparable to standalone, then accuracy drops progressively
2. **TCP and RDMA both affected** — ruling out transport-layer issues
3. **Disabling overlap scheduling doesn't help** — ruling out prefill/transfer concurrency
4. **Removing EAGLE (MTP) doesn't help** — ruling out speculative decoding mismatch
5. **Metadata validation passes** — `bootstrap_room` in MetadataBuffers always matches expected values (zero mismatches across 150+ requests)
6. **Restarting PD recovers accuracy** — 22 questions that were ALL wrong in a degraded session scored 15/22 (68%) correct after PD restart

## Output samples from degraded state (questions 101-150)

The outputs are not "slightly wrong answers" — they show **complete model collapse**:

```
# Question 102 (output_len=21): Truncated garbage
</think></think>: ��?

# Question 120 (output_len=322): Repetitive nonsense
</think></think>Wear:::We just, tryingsamWER '}weWERWERWERWERWERWERWERWER,WERWER;Ω¿Ü≥olver...

# Question 121 (output_len=12253): Infinite repetition
the....... the............. the the.......... the.................

# Question 125 (output_len=2747): Unicode garbage
you to answer the multiple choice question in answer: "the�0ßÞüÎÔÔ...ℎ℉ℎℎℎℎ℔℧℧ℎ℔℔ℎ℧ℎ℧ℎ℧℧℧℧ℎℎ

# Question 130 (output_len=23534): Digit repetition
222222222222>22p2 2>2 2 222]222222222222...

# Question 139 (output_len=6783): Number loop
2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0...

# Question 149 (output_len=12581): Tag repetition
</think></think></think></think></think></think></think>...
```

This pattern — coherent reasoning deteriorating into repetitive loops — is characteristic of **corrupted KV cache values** causing the attention mechanism to lock into degenerate attractors.

## Hypotheses

### Ruled out
- **Transport corruption**: TCP shows the same degradation pattern as RDMA
- **Overlap scheduling race**: `--disable-overlap-schedule` doesn't help
- **Metadata buffer stale data**: `bootstrap_room` validation always passes
- **EAGLE/MTP mismatch**: Removing EAGLE from D node doesn't help
- **Model quantization**: Both FP8 and NVFP4 models degrade in PD mode

### Remaining suspects

1. **KV page data corruption during transfer**: The metadata (`bootstrap_room`) is correct, but the actual KV tensor values at those pages may be corrupted. The RDMA/TCP transfer writes KV data directly into the D node's `kv_buffer` — if the write target addresses are slightly wrong or if old data persists in reused pages, the attention computation would produce garbage.

2. **Cumulative state in Mooncake sessions**: Transfer engine sessions persist across requests. Internal buffer pools, work queues, or completion tracking may accumulate state that degrades transfer fidelity over time.

3. **D-side KV page reuse race**: When a request completes and its KV pages are freed, a new request may receive those same pages. If the new request's RDMA transfer hasn't completed before the decode scheduler reads those pages, it would read stale data from the previous request. The `bootstrap_room` check wouldn't catch this because it validates metadata, not KV data.

4. **`addr_to_rooms_tracker` unbounded growth** (file: `common/conn.py:159`): This set grows with every request and is only cleaned asynchronously by the heartbeat thread. Under sustained load, it increases heartbeat latency, potentially widening timing-sensitive race windows.

## Suggested investigation

1. Add **KV data checksum** verification: compute a hash of KV data on the P side before transfer and verify on the D side after transfer. This would definitively identify whether KV data is corrupted during transfer or during D-side processing.

2. Add **KV page zero-on-free**: When freeing KV pages on the D side, zero the buffers. This prevents stale data from persisting in reused pages.

3. Add **transfer completion barrier**: Before reading transferred KV data, add a `torch.cuda.synchronize()` or memory fence to ensure RDMA writes are visible.

4. Test with **`--max-running-requests 1`** on D side to eliminate all concurrency and see if degradation persists with pure sequential processing.

## Impact

This issue makes PD disaggregation unreliable for tasks requiring long reasoning chains (>5K thinking tokens). For short-output tasks like MMLU (1 token output), the accuracy impact is minimal (~1-2% loss). But for reasoning-heavy benchmarks (GPQA, AIME, HLE), the progressive degradation makes PD mode impractical for production deployment.


### Reproduction

```bash
# P node (prefill)

export NCCL_IB_HCA=mlx5_1
export NCCL_NET_GDR_LEVEL=5
export NCCL_SOCKET_IFNAME=enp97s0f1np1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export FLASHINFER_DISABLE_VERSION_CHECK=1
export SGLANG_ENABLE_JIT_DEEPGEMM=0
export SGLANG_ENABLE_DEEP_GEMM=0
export SGLANG_ENABLE_SPEC_V2=True
export MC_FORCE_TCP=1
export MC_TE_METRIC=1
export MC_TCP_ENABLE_CONNECTION_POOL=1
python3 -m sglang.launch_server     --model-path /models/GLM-5.1-NVFP4     --served-model-name glm-5.1-nvfp4     --reasoning-parser glm45 --tool-call-parser glm47     --nnodes 4 --node-rank 0 --tp 8 --pp-size 4     --dist-init-addr 172.16.106.33:29500     --quantization modelopt_fp4 --kv-cache-dtype bfloat16     --trust-remote-code --mem-fraction-static 0.85     --host 0.0.0.0 --port 5000     --disable-custom-all-reduce --enable-metrics --sleep-on-idle     --attention-backend flashinfer     --fp4-gemm-backend cutlass --moe-runner-backend flashinfer_cutlass     --disable-shared-experts-fusion     --model-loader-extra-config '{"enable_multithread_load": true, "num_threads": 16}'     --json-model-override-args '{"index_topk_pattern": "FFSFSSSFSSFFFSSSFFFSFSSSSSSFFSFFSFFSSFFFFFFSFFFFFSFFSSSSSSFSFFFSFSSSFSFFSFFSSS"}'     --enable-request-time-stats-logging     --disaggregation-mode prefill --disaggregation-ib-device mlx5_1     --disaggregation-transfer-backend mooncake

# D node (decode)
export MC_TE_METRIC=1
export MC_TCP_ENABLE_CONNECTION_POOL=1
export SGLANG_ENABLE_SPEC_V2=1
sglang serve \
  --model-path /models/GLM-5.1-NVFP4 \
  --tp 8 --dp 8 --enable-dp-attention \
  --reasoning-parser glm45 --tool-call-parser glm47 \
  --speculative-algorithm EAGLE --speculative-num-steps 3 --speculative-eagle-topk 1 --speculative-num-draft-tokens 4 \
  --quantization modelopt_fp4 --mem-fraction-static 0.85 --kv-cache-dtype bfloat16 \
  --host 0.0.0.0 --port 30000 --served-model-name glm-5.1-nvfp4 \
  --trust-remote-code --max-running-requests 512 --cuda-graph-max-bs 64 \
  --enable-metrics --enable-request-time-stats-logging \
  --disable-shared-experts-fusion \
  --model-loader-extra-config '{"enable_multithread_load": true, "num_threads": 16}' \
  --json-model-override-args '{"index_topk_pattern": "FFSFSSSFSSFFFSSSFFFSFSSSSSSFFSFFSFFSSFFFFFFSFFFFFSFFSSSSSSFSFFFSFSSSFSFFSFFSSS"}' \
  --disaggregation-mode decode --disaggregation-ib-device mlx5_1 --disaggregation-transfer-backend mooncake
```



### Environment

Prefill:
```
Python: 3.12.3 (main, Mar  3 2026, 12:15:18) [GCC 13.3.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA GeForce RTX 5090
GPU 0,1,2,3,4,5,6,7 Compute Capability: 12.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 13.0, V13.0.88
CUDA Driver Version: 590.44.01
PyTorch: 2.9.1+cu130
sglang: 0.0.0.dev1+ge9d6b9eb2
sglang-kernel: 0.4.1+cu130
flashinfer_python: 0.6.7.post3
flashinfer_cubin: 0.6.7.post3
flashinfer_jit_cache: 0.6.7.post3+cu130
triton: 3.5.1
transformers: 5.3.0
torchao: 0.9.0
numpy: 2.3.5
aiohttp: 3.13.5
fastapi: 0.135.3
huggingface_hub: 1.10.1
interegular: 0.3.3
modelscope: 1.35.4
orjson: 3.11.8
outlines: 0.1.11
packaging: 26.0
psutil: 7.2.2
pydantic: 2.13.0
python-multipart: 0.0.26
pyzmq: 27.1.0
uvicorn: 0.44.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.1.32
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.94.1
litellm: Module Not Found
torchcodec: 0.9.1+cu130
NVIDIA Topology:
        GPU0    GPU1    GPU2    GPU3    GPU4    GPU5    GPU6    GPU7    NIC0    NIC1    CPU Affinity    NUMA Affinity   GPU NUMA ID
GPU0     X      NODE    NODE    NODE    SYS     SYS     SYS     SYS     NODE    NODE    0-127,256-383   0               N/A
GPU1    NODE     X      NODE    NODE    SYS     SYS     SYS     SYS     NODE    NODE    0-127,256-383   0               N/A
GPU2    NODE    NODE     X      NODE    SYS     SYS     SYS     SYS     NODE    NODE    0-127,256-383   0               N/A
GPU3    NODE    NODE    NODE     X      SYS     SYS     SYS     SYS     NODE    NODE    0-127,256-383   0               N/A
GPU4    SYS     SYS     SYS     SYS      X      NODE    NODE    NODE    SYS     SYS     128-255,384-511 1               N/A
GPU5    SYS     SYS     SYS     SYS     NODE     X      NODE    NODE    SYS     SYS     128-255,384-511 1               N/A
GPU6    SYS     SYS     SYS     SYS     NODE    NODE     X      NODE    SYS     SYS     128-255,384-511 1               N/A
GPU7    SYS     SYS     SYS     SYS     NODE    NODE    NODE     X      SYS     SYS     128-255,384-511 1               N/A
NIC0    NODE    NODE    NODE    NODE    SYS     SYS     SYS     SYS      X      PIX
NIC1    NODE    NODE    NODE    NODE    SYS     SYS     SYS     SYS     PIX      X

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


ulimit soft: 1024
```


Decode:
```
Python: 3.12.3 (main, Mar  3 2026, 12:15:18) [GCC 13.3.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA H20-3e
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 13.0, V13.0.88
CUDA Driver Version: 580.95.05
PyTorch: 2.9.1+cu128
sglang: 0.5.10.post2.dev346+g680bd4b42
sglang-kernel: 0.4.1
flashinfer_python: 0.6.7.post3
flashinfer_cubin: 0.6.7.post3
flashinfer_jit_cache: Module Not Found
triton: 3.5.1
transformers: 5.3.0
torchao: 0.9.0
numpy: 2.3.5
aiohttp: 3.13.5
fastapi: 0.135.3
huggingface_hub: 1.8.0
interegular: 0.3.3
modelscope: 1.35.3
orjson: 3.11.8
outlines: 0.1.11
packaging: 26.0
psutil: 7.2.2
pydantic: 2.12.5
python-multipart: 0.0.22
pyzmq: 27.1.0
uvicorn: 0.42.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.1.32
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.88.0
litellm: Module Not Found
torchcodec: 0.9.1
NVIDIA Topology:
        GPU0    GPU1    GPU2    GPU3    GPU4    GPU5    GPU6    GPU7    NIC0    NIC1    CPU Affinity    NUMA Affinity   GPU NUMA ID
GPU0     X      NV18    NV18    NV18    NV18    NV18    NV18    NV18    PIX     PIX     0-47,96-143     0               N/A
GPU1    NV18     X      NV18    NV18    NV18    NV18    NV18    NV18    NODE    NODE    0-47,96-143     0               N/A
GPU2    NV18    NV18     X      NV18    NV18    NV18    NV18    NV18    NODE    NODE    0-47,96-143     0               N/A
GPU3    NV18    NV18    NV18     X      NV18    NV18    NV18    NV18    NODE    NODE    0-47,96-143     0               N/A
GPU4    NV18    NV18    NV18    NV18     X      NV18    NV18    NV18    SYS     SYS     48-95,144-191   1               N/A
GPU5    NV18    NV18    NV18    NV18    NV18     X      NV18    NV18    SYS     SYS     48-95,144-191   1               N/A
GPU6    NV18    NV18    NV18    NV18    NV18    NV18     X      NV18    SYS     SYS     48-95,144-191   1               N/A
GPU7    NV18    NV18    NV18    NV18    NV18    NV18    NV18     X      SYS     SYS     48-95,144-191   1               N/A
NIC0    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS      X      PIX
NIC1    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     PIX      X

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


ulimit soft: 1024
```
