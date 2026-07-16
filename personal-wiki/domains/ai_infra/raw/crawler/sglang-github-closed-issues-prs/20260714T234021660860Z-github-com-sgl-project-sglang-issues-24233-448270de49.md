---
source_id: sglang-github-closed-issues-prs
title: '[Bug] NSA FA3 crash with DP Attention on padded speculative batches'
canonical_url: https://github.com/sgl-project/sglang/issues/24233
captured_at: '2026-07-14T23:40:21.660860+00:00'
content_hash: 448270de496444b90468e785c750af13bc9494d03cfdb99b0cca9575cced9c69
---
# [Bug] NSA FA3 crash with DP Attention on padded speculative batches

URL: https://github.com/sgl-project/sglang/issues/24233
State: closed
Labels: 
Closed at: 2026-07-14T06:29:38Z
Merged at: 

## Summary

NSA FA3 can crash when DP Attention pads a local batch during speculative decoding.

The failure happens because FA3 receives padded Q rows, while the KV metadata still describes the real, unpadded batch.

## Reproduction

Start an NSA model with DP Attention + speculative decoding. Example config used to reproduce:

```bash
python3 -m sglang.launch_server \
  --model-path <NSA_MODEL> \
  --tp 8 \
  --dp 4 \
  --enable-dp-attention \
  --served-model-name GLM-5-FP8-DEBUG \
  --cuda-graph-max-bs 2 \
  --speculative-algorithm NEXTN \
  --speculative-num-steps 3 \
  --speculative-eagle-topk 1 \
  --speculative-num-draft-tokens 4 \
  --page-size 1
```

Then send an asymmetric batch to different DP ranks. This is the core repro client:

```python
import asyncio
import sys
import time

import httpx
import openai

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:30000"
PATTERN = sys.argv[2] if len(sys.argv) > 2 else "1v3"

async def send(client, dp_rank, req_id):
    try:
        t0 = time.time()
        await client.chat.completions.create(
            model="GLM-5-FP8-DEBUG",
            messages=[
                {
                    "role": "user",
                    "content": f"Write an essay about request #{req_id}, be creative.",
                }
            ],
            max_tokens=128,
            extra_body={"routed_dp_rank": dp_rank},
        )
        return True, time.time() - t0
    except Exception as e:
        return False, str(e)[:100]

async def main():
    client = openai.AsyncOpenAI(base_url=f"{BASE_URL}/v1", api_key="none")

    async with httpx.AsyncClient() as hc:
        r = await hc.get(f"{BASE_URL}/health_generate", timeout=5)
        print(f"Health: {r.status_code}")

    print("--- warmup ---")
    print("  warmup:", await send(client, 0, 0))

    dp0, dp1 = map(int, PATTERN.split("v"))
    tasks = []
    rid = 100
    for _ in range(dp0):
        tasks.append(send(client, 0, rid))
        rid += 1
    for _ in range(dp1):
        tasks.append(send(client, 1, rid))
        rid += 1

    results = await asyncio.gather(*tasks, return_exceptions=True)
    ok = sum(1 for r in results if r is not None and r[0])
    print(f"Total: {ok}/{len(results)} ok")
    for r in results:
        print(" ", r)

asyncio.run(main())
```

Run it with `1v3` so DP0 gets 1 request and DP1 gets 3 requests:

```bash
python3 test-dpa-repro.py http://localhost:30000 1v3
```

## Observed Result Without Any Patch

The request batch fails and several scheduler ranks report the same FA3 error:

```text
RuntimeError: batch_size must be equal to batch_size_k
```

A representative stack trace is:

```text
File "/sgl-workspace/sglang/python/sglang/srt/layers/attention/nsa_backend.py", line 1584, in forward_decode
  return self._forward_fa3(
File "/sgl-workspace/sglang/python/sglang/srt/layers/attention/nsa_backend.py", line 1633, in _forward_fa3
  o = flash_attn_with_kvcache(
File "/usr/local/lib/python3.12/dist-packages/sgl_kernel/flash_attn.py", line 189, in flash_attn_with_kvcache
  out, softmax_lse, *rest = torch.ops.sgl_kernel.fwd.default(
RuntimeError: batch_size must be equal to batch_size_k
```

After the first rank fails, other ranks start reporting distributed cleanup errors such as:

```text
[c10d] recvValue failed ... Failed to recv, got 0 bytes. Connection was likely closed. Did the remote server shutdown or crash?
```

In Kubernetes, this shows up as failed in-flight requests followed by scheduler/model-worker process termination and pod restart.

## Expected Result

Attention should run only on the real, unpadded batch. DP padding rows are only needed for the later MLP sync path and should not be treated as real FA3 Q rows.

Candidate fix:

#24235
