---
source_id: sglang-github-closed-issues-prs
title: '[Bug] HiSparse DeepSeek-V4 decode caps prompt length at the SWA pool size
  instead of the full pool'
canonical_url: https://github.com/sgl-project/sglang/issues/30401
captured_at: '2026-07-10T23:37:20.314303+00:00'
content_hash: ff289b89f9d11d171bfc7e40fadb247ec42895fe026287a77ecbffc51df9f542
---
# [Bug] HiSparse DeepSeek-V4 decode caps prompt length at the SWA pool size instead of the full pool

URL: https://github.com/sgl-project/sglang/issues/30401
State: closed
Labels: 
Closed at: 2026-07-10T07:27:04Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

Hi team, thanks for the great work on sglang and HiSparse 🙏

## Summary

On the **decode** node with **DeepSeek-V4-Flash** (hybrid SWA) + HiSparse under PD disaggregation, the per-request admission limit is clamped to the **SWA pool** (`full × swa_full_tokens_ratio`) instead of the **full pool**, so long prompts are rejected with `exceeds the maximum number of tokens`. Disabling HiSparse (same config otherwise) removes the limit. Root cause: the HiSparse allocator wrapper hides `alloc_extend_swa_tail`, forcing decode to pre-allocate SWA at *full prompt length*.

## Environment

- sglang **0.5.14**, 8×H100, `tp=4 dp=4 --enable-dp-attention`, PD disaggregation (`mooncake`), `--moe-runner-backend marlin`
- Model: **DeepSeek-V4-Flash** (`DeepseekV4ForCausalLM`), hybrid SWA (`sliding_window=128`), `--swa-full-tokens-ratio 0.1`
- Decode HiSparse: `{"top_k":2048,"device_buffer_size":4096,"host_to_device_ratio":10}`

## Expected vs. Actual

- **Expected:** with a 128 sliding window, a single long prompt is admissible up to the full logical budget (as it is when HiSparse is off).
- **Actual (HiSparse on):**
  ```
  Request <rid> exceeds the maximum number of tokens: 512000 > 177920
  ```

## Evidence (same 512K input, HiSparse on vs off)

| | HiSparse **ON** | HiSparse **OFF** |
|---|---|---|
| decode `full` / `swa` pool | 1779456 / 177920 | 1470720 / 146944 |
| per-request admission limit | **swa = 177920** | **full = 1470720** |
| `exceeds the maximum number of tokens` | **193** | **0** |
| 512K input | rejected (HTTP 400) | admitted |

The limit is *not* about SWA capacity: with HiSparse off the SWA pool is even smaller (146944) yet **0** rejections — the limit source changes from the SWA pool to the full pool. (The **prefill** role never rejects these inputs; it uses the full pool as its limit.)

## Root Cause (paths in `python/sglang/srt/`, 0.5.14)

1. `disaggregation/decode.py:549` — admission check `len(req.origin_input_ids) > self.max_total_num_tokens`.
2. `disaggregation/decode.py:337-345` — clamps `max_total_num_tokens` to the SWA pool **only when** `is_hybrid_swa and not self._uses_swa_tail_prealloc()` (comment: *"Fallback for SWA allocators that still allocate the SWA pool at full prompt length"*).
3. `disaggregation/decode.py:348-353` — `_uses_swa_tail_prealloc()` requires the allocator to have `alloc_extend_swa_tail`, which is defined **only** on `SWATokenToKVPoolAllocator` (`mem_cache/allocator/swa.py:209`).
4. `model_executor/model_runner_kv_cache_mixin.py:860-861` builds a `SWATokenToKVPoolAllocator` (has the method), then `:906-911` **wraps** it in `DeepSeekV4HiSparseTokenToKVPoolAllocator` (`mem_cache/allocator/hisparse.py:276`), which does **not** define or forward `alloc_extend_swa_tail`.

So the wrapper flips `_uses_swa_tail_prealloc()` `True → False`, triggering the full-prompt-length SWA prealloc fallback and collapsing the per-request limit to the SWA pool. **In short: the HiSparse wrapper drops the wrapped SWA allocator's `alloc_extend_swa_tail`, so decode reserves SWA for the entire prompt instead of just the window tail.**

## Suggested Fix

Implement/forward `alloc_extend_swa_tail` on `DeepSeekV4HiSparseTokenToKVPoolAllocator` (delegating to the underlying `SWATokenToKVPoolAllocator` should suffice, since HiSparse only changes the c4 pool, not SWA), so `_uses_swa_tail_prealloc()` returns `True` and the artificial per-request limit is lifted.


Thanks in advance — happy to provide more logs! cc @alphabetc1 @yhyang201 

### Reproduction

prefill:
```
export CUDA_VISIBLE_DEVICES=0,1,2,3
sglang serve \
  --trust-remote-code \
  --model-path /models/preset/deepseek-ai/DeepSeek-V4-Flash/v1.0 \
  --tokenizer-path /models/preset/deepseek-ai/DeepSeek-V4-Flash/v1.0 \
  --tp 4 \
  --dp 4 \
  --enable-dp-attention \
  --moe-runner-backend marlin \
  --mem-fraction-static 0.95 \
  --swa-full-tokens-ratio 0.1 \
  --disaggregation-mode prefill \
  --disaggregation-transfer-backend mooncake \
  --dist-init-addr 127.0.0.1:30135 \
  --disaggregation-bootstrap-port 8998 \
  --host 0.0.0.0 \
  --port 30000
```

decode:
```
export CUDA_VISIBLE_DEVICES=4,5,6,7
sglang serve \
  --trust-remote-code \
  --model-path /models/preset/deepseek-ai/DeepSeek-V4-Flash/v1.0 \
  --tokenizer-path /models/preset/deepseek-ai/DeepSeek-V4-Flash/v1.0 \
  --tp 4 \
  --dp 4 \
  --enable-dp-attention \
  --moe-runner-backend marlin \
  --mem-fraction-static 0.95 \
  --swa-full-tokens-ratio 0.1 \
  --cuda-graph-max-bs 128 \
  --disable-radix-cache \
  --enable-hisparse \
  --hisparse-config '{"top_k": 2048, "device_buffer_size": 4096, "host_to_device_ratio": 10}' \
  --disaggregation-mode decode \
  --disaggregation-transfer-backend mooncake \
  --dist-init-addr 127.0.0.1:30435 \
  --host 0.0.0.0 \
  --port 30001
```

router:
```
python3 -m sglang_router.launch_router \
  --pd-disaggregation \
  --prefill http://127.0.0.1:30000 8998 \
  --decode http://127.0.0.1:30001 \
  --host 0.0.0.0 --port 8000 \
  --prefill-policy round_robin \
  --disable-circuit-breaker \
  --health-check-interval-secs 999999
```

bench:
```bash
python -m sglang.bench_serving \
  --backend sglang \
  --base-url http://127.0.0.1:8000 \
  --model /models/preset/deepseek-ai/DeepSeek-V4-Flash/v1.0 \
  --dataset-name random \
  --num-prompts 192 \
  --random-input-len 512000 \
  --random-output-len 10240 \
  --random-range-ratio 1.0 \
  --max-concurrency 64 \
  --flush-cache \
  --request-rate 0.3
```


### Environment

`lmsysorg/sglang:v0.5.14`

```
python3 -m sglang.check_env
Python: 3.12.3 (main, Mar 23 2026, 19:04:32) [GCC 13.3.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA H100 80GB HBM3
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 13.0, V13.0.88
CUDA Driver Version: 570.133.20
PyTorch: 2.11.0+cu130
sglang: 0.5.14
sglang-kernel: 0.4.4
flashinfer_python: 0.6.12
flashinfer_cubin: 0.6.12
flashinfer_jit_cache: 0.6.12+cu130
triton: 3.6.0
transformers: 5.8.1
torchao: 0.17.0+cu130
numpy: 2.3.5
aiohttp: 3.14.1
fastapi: 0.138.1
huggingface_hub: 1.21.0
interegular: 0.3.3
modelscope: 1.37.1
orjson: 3.11.9
outlines: 0.1.11
packaging: 26.2
psutil: 7.2.2
pydantic: 2.13.4
python-multipart: 0.0.32
pyzmq: 27.1.0
uvicorn: 0.49.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.2.1
openai: 2.6.1
tiktoken: 0.13.0
anthropic: 0.112.0
litellm: Module Not Found
torchcodec: 0.11.1+cu130
NVIDIA Topology: 
        GPU0    GPU1    GPU2    GPU3    GPU4    GPU5    GPU6    GPU7    NIC0    NIC1    NIC2    NIC3    NIC4    NIC5    NIC6    NIC7    CPU Affinity    NUMA Affinity   GPU NUMA ID
GPU0     X      NV18    NV18    NV18    NV18    NV18    NV18    NV18    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     0-47,96-143     0               N/A
GPU1    NV18     X      NV18    NV18    NV18    NV18    NV18    NV18    NODE    PIX     NODE    NODE    SYS     SYS     SYS     SYS     0-47,96-143     0               N/A
GPU2    NV18    NV18     X      NV18    NV18    NV18    NV18    NV18    NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     0-47,96-143     0               N/A
GPU3    NV18    NV18    NV18     X      NV18    NV18    NV18    NV18    NODE    NODE    NODE    PIX     SYS     SYS     SYS     SYS     0-47,96-143     0               N/A
GPU4    NV18    NV18    NV18    NV18     X      NV18    NV18    NV18    SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    48-95,144-191   1               N/A
GPU5    NV18    NV18    NV18    NV18    NV18     X      NV18    NV18    SYS     SYS     SYS     SYS     NODE    PIX     NODE    NODE    48-95,144-191   1               N/A
GPU6    NV18    NV18    NV18    NV18    NV18    NV18     X      NV18    SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    48-95,144-191   1               N/A
GPU7    NV18    NV18    NV18    NV18    NV18    NV18    NV18     X      SYS     SYS     SYS     SYS     NODE    NODE    NODE    PIX     48-95,144-191   1               N/A
NIC0    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS      X      NODE    NODE    NODE    SYS     SYS     SYS     SYS
NIC1    NODE    PIX     NODE    NODE    SYS     SYS     SYS     SYS     NODE     X      NODE    NODE    SYS     SYS     SYS     SYS
NIC2    NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE     X      NODE    SYS     SYS     SYS     SYS
NIC3    NODE    NODE    NODE    PIX     SYS     SYS     SYS     SYS     NODE    NODE    NODE     X      SYS     SYS     SYS     SYS
NIC4    SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS      X      NODE    NODE    NODE
NIC5    SYS     SYS     SYS     SYS     NODE    PIX     NODE    NODE    SYS     SYS     SYS     SYS     NODE     X      NODE    NODE
NIC6    SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE     X      NODE
NIC7    SYS     SYS     SYS     SYS     NODE    NODE    NODE    PIX     SYS     SYS     SYS     SYS     NODE    NODE    NODE     X 

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


ulimit soft: 1000000
```
