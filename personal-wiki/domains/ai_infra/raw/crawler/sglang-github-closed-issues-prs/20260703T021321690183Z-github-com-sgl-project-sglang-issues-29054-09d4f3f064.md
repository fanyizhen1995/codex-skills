---
source_id: sglang-github-closed-issues-prs
title: '[Bug] PP disagg prefill can mismatch PP1 ForwardBatch with PP proxy tensor
  under HiCache pressure'
canonical_url: https://github.com/sgl-project/sglang/issues/29054
captured_at: '2026-07-03T02:13:21.690183+00:00'
content_hash: 09d4f3f064cf9139a3d876569affa4a99d814ac0c7d731b67df6eb3bc1d64870
---
# [Bug] PP disagg prefill can mismatch PP1 ForwardBatch with PP proxy tensor under HiCache pressure

URL: https://github.com/sgl-project/sglang/issues/29054
State: closed
Labels: 
Closed at: 2026-07-02T09:13:36Z
Merged at: 

## Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

## Describe the bug

In PP disaggregated prefill with HiCache enabled, PP1 can crash because its current `ForwardBatch` token metadata does not match the PP proxy tensor received from PP0. The first visible failure is in RoPE reshape, but the shape numbers indicate a PP handoff invariant violation rather than a RoPE-specific issue.

Original incident:

```text
File "/sgl-workspace/sglang/python/sglang/srt/layers/rotary_embedding/base.py", line 350, in forward_cuda
    q_rope = query.view(batch_size, -1, self.head_size)
RuntimeError: shape '[65, -1, 64]' is invalid for input of size 827392
```

A later reproduction showed the same failure mode:

```text
2026-06-23T15:16:14Z [PP1 ATTN_CP0 TP0] Scheduler hit an exception
File "/sgl-workspace/sglang/python/sglang/srt/layers/rotary_embedding/base.py", line 350, in forward_cuda
    q_rope = query.view(batch_size, -1, self.head_size)
RuntimeError: shape '[68, -1, 64]' is invalid for input of size 1818624
```

The reproduced crash happened on all PP1 CP ranks. PP0 then failed secondarily with Gloo peer-closed errors after PP1 exited.

Observed invariant violation:

```text
Reproduced incident:
positions batch_size on PP1 = 68
query/proxy tensor elements = 1818624
local q heads = 32
head_size = 64
proxy local token count = 1818624 / (32 * 64) = 888
68 != 888

Original incident:
positions batch_size on PP1 = 65
query/proxy tensor elements = 827392
proxy local token count = 827392 / (32 * 64) = 404
65 != 404
```

This suggests PP1 is launching one `ForwardBatch` while consuming a proxy tensor produced for another batch.

Relevant code path:

```text
python/sglang/srt/managers/scheduler_pp_mixin.py:event_loop_pp_disagg_prefill
  process_prefill_chunk()
  get_new_batch_prefill()
  _pp_recv_proxy_tensors()
  _pp_launch_batch()

python/sglang/srt/managers/scheduler_pp_mixin.py:_pp_recv_proxy_tensors
```

The proxy channel is typed by `msg_type="proxy"`, but I do not see an invariant check that the received proxy tensor corresponds to the receiver's current batch, such as rid list, batch id, or token count. If PP0 and PP1 diverge in which microbatch is current under HiCache/disaggregated/chunked-prefill pressure, FIFO proxy receive can feed a stale/wrong proxy tensor into PP1.

Related issues searched:

- [PP + HiCache] HiCache Consistency Fix Plan #22607 comment reports a very similar PP-path RoPE failure with `cp 8 + pp2 + L2` on GLM-5.1: `event_loop_pp -> _pp_launch_batch -> run_batch -> nsa_indexer -> rotary_embedding/base.py`, failing at `q_rope = query.view(batch_size, -1, self.head_size)` with `RuntimeError: shape '[2048, -1, 64]' is invalid for input of size 16384`.

## Reproduction

Model used: GLM-5.2-FP8.

This is intermittent, but I reproduced it with ordinary `/generate` traffic under shared-prefix HiCache pressure. The reproduced crash did not require a valid `/abort_request`; abort attempts sent to the router returned 404 and were ineffective. The effective load was normal generation requests with long shared prefixes.

Server shape:

```bash
python3 -m sglang.launch_server \
  --model-path /path/to/GLM-5.2-FP8 \
  --tokenizer-path /path/to/GLM-5.2-FP8 \
  --trust-remote-code \
  --quantization fp8 \
  --served-model-name GLM-5.2 \
  --disaggregation-mode prefill \
  --disaggregation-transfer-backend mooncake \
  --host 0.0.0.0 \
  --tp-size 8 \
  --pp-size 2 \
  --page-size 64 \
  --kv-cache-dtype fp8_e4m3 \
  --mem-fraction-static 0.88 \
  --chunked-prefill-size 16384 \
  --max-prefill-tokens 16384 \
  --max-running-requests 256 \
  --context-length 350000 \
  --enable-cache-report \
  --enable-metrics \
  --disable-cuda-graph \
  --moe-dense-tp-size 1 \
  --enable-nsa-prefill-context-parallel \
  --attn-cp-size 8 \
  --nsa-prefill-cp-mode round-robin-split \
  --enable-hierarchical-cache \
  --hicache-size 160 \
  --hicache-mem-layout page_first
```

Client load pattern used for reproduction:

```python
import asyncio
import aiohttp
import random

BASE = "http://127.0.0.1:8000"
COMMON = [1000 + (i % 1000) for i in range(32768)]
RESIDUALS = [520, 3232, 520, 3232, 576, 384, 3520, 512, 3264]


def input_ids(total, salt):
    unique = 64
    return COMMON[: total - unique] + [200000 + ((salt + i) % 20000) for i in range(unique)]


async def generate(session, rid, n):
    payload = {
        "rid": rid,
        "input_ids": input_ids(n, abs(hash(rid)) % 100000),
        "sampling_params": {"temperature": 0, "max_new_tokens": 1, "ignore_eos": True},
    }
    async with session.post(BASE + "/generate", json=payload, timeout=aiohttp.ClientTimeout(total=240)) as r:
        await r.text()
        return r.status


async def seed(session):
    lengths = [36864, 36928, 37056, 37376, 40000, 65536, 98304]
    sem = asyncio.Semaphore(32)

    async def one(i):
        async with sem:
            return await generate(session, f"seed-{i}", lengths[i % len(lengths)])

    await asyncio.gather(*(one(i) for i in range(96)))


async def wave(session, w, count=192, concurrency=96):
    sem = asyncio.Semaphore(concurrency)

    async def one(i):
        residual = RESIDUALS[(i + w * 3) % len(RESIDUALS)]
        total = 65536 + residual
        async with sem:
            return await generate(session, f"repro-{w}-{i}-{residual}", total)

    return await asyncio.gather(*(one(i) for i in range(count)))


async def main():
    conn = aiohttp.TCPConnector(limit=256, limit_per_host=256, force_close=True)
    async with aiohttp.ClientSession(connector=conn) as session:
        await seed(session)
        for w in range(6):
            await wave(session, w)

asyncio.run(main())
```

The crash is intermittent; the key characteristics are:

- `pp-size=2`, `tp-size=8`, `attn-cp-size=8`
- disaggregated prefill + Mooncake transfer
- HiCache enabled
- chunked prefill enabled
- shared-prefix long prompts with high cache reuse
- mixed residual lengths around hundreds to a few thousand tokens
- high concurrency so bootstrap/inflight queues are non-empty

## Environment

```text
SGLang image: lmsysorg/sglang:v0.5.13.post1
SGLANG_BUILD_COMMIT=85fd90072d1a9f2432842b03588f63b745e524e4

python3 -m sglang.check_env:

Python: 3.12.3 (main, Mar 23 2026, 19:04:32) [GCC 13.3.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA H100 80GB HBM3
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 13.0, V13.0.88
CUDA Driver Version: 590.48.01
PyTorch: 2.11.0+cu130
sglang: 0.5.13.post1
sglang-kernel: 0.4.3
flashinfer_python: 0.6.12
flashinfer_cubin: 0.6.12
flashinfer_jit_cache: 0.6.12+cu130
triton: 3.6.0
transformers: 5.8.1
torchao: 0.17.0+cu130
numpy: 2.3.5
aiohttp: 3.14.1
fastapi: 0.137.0
huggingface_hub: 1.19.0
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
anthropic: 0.109.1
litellm: Module Not Found
torchcodec: 0.11.1+cu130
ulimit soft: 1048576
```
