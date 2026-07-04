---
source_id: sglang-github-closed-issues-prs
title: Triton RMSNorm kernel underutilizes T4/A10G/A100 SMs for large contexts (NCU
  data)
canonical_url: https://github.com/sgl-project/sglang/issues/24353
captured_at: '2026-07-04T02:13:49.127434+00:00'
content_hash: 1da269faf5fe289b9c15e45f948e8460f396b5b1dc5aced24693ceb5f7c5bc64
---
# Triton RMSNorm kernel underutilizes T4/A10G/A100 SMs for large contexts (NCU data)

URL: https://github.com/sgl-project/sglang/issues/24353
State: closed
Labels: inactive
Closed at: 2026-07-04T00:38:21Z
Merged at: 

Hi @BBuf,

The current `triton_one_pass_rms_norm` kernel uses a static heuristic `block_size_seq = min(16, next_power_of_2(max(1, S // 512)))` with hardcoded `num_warps=4`. NCU profiling shows this causes severe SM underutilization for large sequence lengths (S≥4096), leaving ~70% of GPU capacity idle. A simple config change to `BLOCK_SIZE_N=2, num_warps=8` improves memory throughput **4.3×** and reduces latency **~24%** at 32K context.

## Environment

- GPU: NVIDIA A100 (also tested on T4/A10G)
- SGLang: latest main
- Test shape: S=32768, D=4096

## NCU Metrics

| Config | Registers/Thread | Memory Throughput % | Warps Active (Occupancy) % | Time (ms) |
|--------|-----------------|---------------------|---------------------------|-----------|
| **BS=2, W=8** (proposed) | **26** | **36.74%** | **96.11%** | **0.451** |
| BS=16, W=4 (current) | 96 | 8.49% | 28.36% | 0.593 |

## Benchmark Across Sequence Lengths

| S | Current Config (Time) | Best Config (Time) | Speedup |
|---|----------------------|-------------------|---------|
| 512 | (1, 4) = 0.022 ms | (1, 4) = 0.022 ms | 0% |
| 1024 | (2, 4) = 0.026 ms | (4, 8) = 0.026 ms | ~2% |
| 2048 | (4, 4) = 0.043 ms | (4, 8) = 0.040 ms | ~5% |
| 4096 | (8, 4) = 0.087 ms | **(2, 8) = 0.070 ms** | **18.7%** |
| 8192 | (16, 4) = 0.160 ms | **(2, 8) = 0.125 ms** | **21.9%** |
| 16384 | (16, 4) = 0.306 ms | **(2, 8) = 0.234 ms** | **23.4%** |
| 32768 | (16, 4) = 0.593 ms | **(2, 8) = 0.451 ms** | **23.9%** |
128K   | (16, 4) = 2.2635 ms            | (2, 8) = 1.7133 ms        | 24.31% faster

> **Note:** 128K matches LLaMA 3.1 context length. The ~24% speedup holds consistently from 16K to 128K, confirming the issue is not specific to any single shape.

## Root Cause

1. **Register pressure:** Current config uses 96 registers/thread. A100 has 64K registers/SM → max ~6-7 blocks/SM concurrently. With only 2048 total blocks at S=32K, many SMs sit idle.
2. **Low occupancy:** 28% warps active means GPU is stalled waiting for memory or has insufficient parallel work.
3. **Poor memory throughput:** 8.5% bandwidth utilization indicates memory pipeline is underfed.

Proposed config (26 registers/thread, 16384 blocks) allows 8 blocks/SM concurrently with deep queue → 96% occupancy → 4× memory throughput.

## Proposed Fix

Replace static heuristic with shape-aware config:

```python
# A potential dynamic scaling logic to avoid compilation overhead:
def _get_rms_config(S: int):
    if S>=4096:
        return 2, 8    # (block_size_seq, num_warps) -> Maximizes throughput for long context
    elif S>=1024:
        return 4, 8    # Transition zone
    else:
        # Original safe fallback for smaller sequences
        block_size_seq = min(16, triton.next_power_of_2(max(1, S // 512)))
        return block_size_seq, 4
```


I am sharing these NCU metrics here, as this could easily double the memory throughput for long-context inference without introducing any stability risks. Would love to hear your thoughts on this!
