---
source_id: sglang-github-closed-issues-prs
title: 'fix(xpu): use memory_reserved() instead of memory_allocated() for accurate
  free-memory estimate'
canonical_url: https://github.com/sgl-project/sglang/pull/30032
captured_at: '2026-07-04T02:13:49.134107+00:00'
content_hash: e599a6bb43903824951a5434322347658dc59d44bdfc568d8a00eb79d158dad1
---
# fix(xpu): use memory_reserved() instead of memory_allocated() for accurate free-memory estimate

URL: https://github.com/sgl-project/sglang/pull/30032
State: closed
Labels: 
Closed at: 2026-07-03T10:55:56Z
Merged at: 

## Problem

`get_available_gpu_memory()` on Intel XPU uses `torch.xpu.memory_allocated()` to estimate free GPU memory.  `memory_allocated()` only counts tensors that are **currently active** inside the PyTorch caching allocator; it does **not** include memory the allocator has pre-claimed from the Level Zero driver as a pool but has not yet filled with live tensors.

This causes `get_available_gpu_memory()` to **overestimate** free memory, which in turn causes the KV-cache sizing formula:

```python
rest_memory = available_gpu_memory - pre_model_load_memory * (1 - mem_fraction_static)
```

to allocate a KV cache that is larger than what the device can actually support, resulting in OOM during inference (SIGKILL / watchdog timeout).

Additionally, `torch.xpu.mem_get_info()` is **unreliable** on Intel XPU hardware — it always returns the full hardware capacity as free regardless of how much memory is actually allocated, making it unsuitable as an alternative.

This was confirmed experimentally:

```python
t = torch.zeros(500_000_000, dtype=torch.bfloat16, device='xpu:0')  # 0.5 GB
print(torch.xpu.memory_allocated(0))   # 0.500 GB  ✓ (correct)
print(torch.xpu.memory_reserved(0))    # 0.501 GB  ✓ (correct)
free, total = torch.xpu.mem_get_info(0)
print(free)  # 25.669 GB  ✗ (same as before allocation — completely ignores the 0.5 GB)
```

## Fix

Switch from `memory_allocated()` to `memory_reserved(gpu_id)`.

`memory_reserved()` tracks the allocator's **total** Level Zero pool claim — both active tensors and the allocator's internal free pool. This gives a conservative but correct free-memory estimate.

```python
# Before
used_memory = torch.xpu.memory_allocated()

# After
used_memory = torch.xpu.memory_reserved(gpu_id)
```

## Impact

- Prevents KV-cache over-allocation on Intel XPU devices
- `memory_reserved() >= memory_allocated()` always, so this is strictly more conservative
- For models where `reserved ≈ allocated` (normal weight loading path), the behavior is identical
- The difference matters when the XPU caching allocator pre-claims a large Level Zero pool before filling it with live tensors

## Test

Validated on Intel Battlemage XPU (23.91 GiB usable) with Gemma-7B (TP=1) and Apertus-8B (TP=2) in the SGLang P1 accuracy evaluation suite.





<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28655988717](https://github.com/sgl-project/sglang/actions/runs/28655988717)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:hourglass_flowing_sand: [Run #28655988542](https://github.com/sgl-project/sglang/actions/runs/28655988542)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
