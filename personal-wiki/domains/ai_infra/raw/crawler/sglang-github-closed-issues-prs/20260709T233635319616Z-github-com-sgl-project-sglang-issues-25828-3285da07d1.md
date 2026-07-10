---
source_id: sglang-github-closed-issues-prs
title: '[Bug] NSATokenToKVPool does not implement KVCache.get_cpu_copy() interface,
  crashes retract path'
canonical_url: https://github.com/sgl-project/sglang/issues/25828
captured_at: '2026-07-09T23:36:35.319616+00:00'
content_hash: 3285da07d1ebe56b7f6872234de9d229cf5cc9090b8d8a12315c0500c8a7d970
---
# [Bug] NSATokenToKVPool does not implement KVCache.get_cpu_copy() interface, crashes retract path

URL: https://github.com/sgl-project/sglang/issues/25828
State: closed
Labels: 
Closed at: 2026-07-09T08:06:44Z
Merged at: 

## Describe the bug

When KV cache reaches saturation under PD-disaggregated decode with NSA attention, `retract_decode()` calls `NSATokenToKVPool.get_cpu_copy(mamba_indices=...)` and later `NSATokenToKVPool.load_cpu_copy(mamba_indices=...)`, but neither method accepts this keyword argument. The resulting `TypeError` kills the scheduler.

`NSATokenToKVPool` inherits `MLATokenToKVPool` and overrides both `get_cpu_copy()` and `load_cpu_copy()`, but the overrides drop the `mamba_indices=None` parameter that the base class `KVCache` defines and all other subclasses implement:

```
KVCache (base)                          ← defines interface
├── get_cpu_copy(self, indices, mamba_indices=None)
└── load_cpu_copy(self, kv, indices, mamba_indices=None)

MHATokenToKVPool(KVCache)               ✓ (indices, mamba_indices=None)
HybridLinearKVPool(KVCache)             ✓ (indices, mamba_indices=None)  ← only one that uses it
MLATokenToKVPool(KVCache)               ✓ (indices, mamba_indices=None)
  └── NSATokenToKVPool(MLATokenToKVPool)  ✗ (indices)                   ← missing mamba_indices
```

**Call chain** (v0.5.12):

```
Scheduler loop (scheduler.py:1773)
  │  check_decode_mem() returns False (KV usage >= 1.0)
  │
  ▼
batch.retract_decode(server_args)  (schedule_batch.py:1407)
  │  picks requests to evict in reverse arrival order
  │
  ├─ if server_args.disaggregation_mode == "decode":  (line 2249)
  │     req.offload_kv_cache(req_to_token_pool, token_to_kv_pool_allocator)
  │
  ▼
Req.offload_kv_cache()  (schedule_batch.py:1292)
  │  self.kv_cache_cpu = token_to_kv_pool_allocator.get_cpu_copy(
  │      token_indices, mamba_indices=self.mamba_pool_idx
  │  )
  │
  ▼
TokenToKVPoolAllocator.get_cpu_copy()  (allocator.py:172)
  │  return self._kvcache.get_cpu_copy(indices, mamba_indices=mamba_indices)
  │
  ▼
NSATokenToKVPool.get_cpu_copy(self, indices)  (memory_pool.py:2145)
  │
  ╳  TypeError: got an unexpected keyword argument 'mamba_indices'
```

[scheduler.py:1773](https://github.com/sgl-project/sglang/blob/127b9e3283f7c2a43234b852ff5c9f1796d53624/python/sglang/srt/managers/scheduler.py#L1773) → [schedule_batch.py:2249](https://github.com/sgl-project/sglang/blob/127b9e3283f7c2a43234b852ff5c9f1796d53624/python/sglang/srt/managers/schedule_batch.py#L2249) → [schedule_batch.py:1292](https://github.com/sgl-project/sglang/blob/127b9e3283f7c2a43234b852ff5c9f1796d53624/python/sglang/srt/managers/schedule_batch.py#L1292-L1294) → [allocator.py:172](https://github.com/sgl-project/sglang/blob/127b9e3283f7c2a43234b852ff5c9f1796d53624/python/sglang/srt/mem_cache/allocator.py#L171-L172) → [**memory_pool.py:2145**](https://github.com/sgl-project/sglang/blob/127b9e3283f7c2a43234b852ff5c9f1796d53624/python/sglang/srt/mem_cache/memory_pool.py#L2145) 💥

The same pattern exists on the restore path: [`load_kv_cache()`](https://github.com/sgl-project/sglang/blob/127b9e3283f7c2a43234b852ff5c9f1796d53624/python/sglang/srt/managers/schedule_batch.py#L1297-L1302) passes `mamba_indices` → [`NSATokenToKVPool.load_cpu_copy(self, kv_cache_cpu_dict, indices)`](https://github.com/sgl-project/sglang/blob/127b9e3283f7c2a43234b852ff5c9f1796d53624/python/sglang/srt/mem_cache/memory_pool.py#L2159) also missing it.

The bug fires when all three conditions are met:
1. NSA attention model (e.g. GLM-5.1)
2. KV cache token usage reaches ~1.0
3. Scheduler enters `retract_decode()` → `offload_kv_cache()` in disaggregation decode mode

**Crash trace from production**:

```
[22:54:04 DP28] Decode batch, #running-req: 1, #token: 364032, token usage: 1.00,
                pre-allocated usage: 0.88, #prealloc-req: 44, #retracted-req: 0

[22:54:05 DP28] Scheduler hit an exception:
Traceback (most recent call last):
    retracted_reqs, new_token_ratio, reqs_to_abort = batch.retract_decode(
TypeError: NSATokenToKVPool.get_cpu_copy() got an unexpected keyword argument 'mamba_indices'
```

**Fix** — add `mamba_indices=None` to both overrides and pass through to `super()`:

```python
# memory_pool.py:2145
def get_cpu_copy(self, indices, mamba_indices=None):
    kv_cache_cpu = super().get_cpu_copy(indices, mamba_indices=mamba_indices)
    ...

# memory_pool.py:2159
def load_cpu_copy(self, kv_cache_cpu_dict, indices, mamba_indices=None):
    super().load_cpu_copy(kv_cache_cpu_dict["kv"], indices, mamba_indices=mamba_indices)
    ...
```

This is safe because `mamba_indices` is only consumed by [`HybridLinearKVPool`](https://github.com/sgl-project/sglang/blob/127b9e3283f7c2a43234b852ff5c9f1796d53624/python/sglang/srt/mem_cache/memory_pool.py#L1568-L1580) (Mamba+Attention hybrid models). All other subclasses including NSA's parent [`MLATokenToKVPool`](https://github.com/sgl-project/sglang/blob/127b9e3283f7c2a43234b852ff5c9f1796d53624/python/sglang/srt/mem_cache/memory_pool.py#L1814) accept and ignore it.

## Reproduction

```bash
python3 -m sglang.launch_server \
  --model-path GLM-5.1-FP8 \
  --tp 32 --dp 32 \
  --mem-fraction-static 0.8 \
  --max-running-requests 256 \
  --kv-cache-dtype fp8_e4m3 \
  --disaggregation-mode decode
```

Send sustained traffic until any single DP rank reaches `token usage: 1.00`. The scheduler will attempt `retract_decode()` → `TypeError` → crash.

## Environment

- SGLang v0.5.12 (`lmsysorg/sglang:v0.5.12`)
- Model: GLM-5.1-FP8 (context_length=202752, NSA attention)
- 4 nodes × 8× H800 80GB, TP=32, DP=32
- PD disaggregation mode (decode side)
