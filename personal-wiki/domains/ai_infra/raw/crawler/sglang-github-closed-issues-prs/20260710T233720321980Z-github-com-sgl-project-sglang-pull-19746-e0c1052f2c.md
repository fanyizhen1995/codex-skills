---
source_id: sglang-github-closed-issues-prs
title: '[P/D disagg] - support decode side radix cache'
canonical_url: https://github.com/sgl-project/sglang/pull/19746
captured_at: '2026-07-10T23:37:20.321980+00:00'
content_hash: e0c1052f2cf0a63c6d07a41afb93ac634cfc2d19cd2ad8d5ce079111e0d8bfbd
---
# [P/D disagg] - support decode side radix cache

URL: https://github.com/sgl-project/sglang/pull/19746
State: closed
Labels: high priority, run-ci
Closed at: 2026-05-01T13:55:35Z
Merged at: 2026-05-01T13:55:35Z

## Summary

In PD disaggregation, the decode worker can now use radix cache to reuse shared prefixes and request only the delta KV from prefill instead of transferring the full prefix on every turn.

This is enabled with `--disaggregation-decode-enable-radix-cache` on the decode server.

For now, this path is supported only with `--disaggregation-transfer-backend nixl`. `server_args.py` now rejects other transfer backends early when the decode radix cache flag is enabled. Mooncake support will follow in a separate PR.

## Main Changes

- **Decode scheduler**
  - Match incoming requests against the decode-side radix tree.
  - Lock matched prefix nodes for the request lifetime.
  - Pre-allocate only the delta KV pages beyond the matched prefix.
- **Decode -> prefill protocol**
  - Plumb `decode_prefix_len` from decode to prefill for the NIXL path.
  - Allow full-prefix hits where decode may need no KV pages transferred.
- **Prefill transfer path**
  - Initialize the sender with only the unsent delta pages.
  - Keep the chunked transfer cursor monotonic when decode already has part of the prefix.
  - Skip empty non-last chunks so the sender/receiver chunk protocol stays consistent.
- **Correctness / cleanup**
  - Align matched prefix length to page boundaries for paged KV allocators.
  - Guard lock release / cleanup paths for transfer-failure cases.
  - Batch finished prebuilt frees through the free-group path.
- **CLI / config**
  - The user-facing switch is `--disaggregation-decode-enable-radix-cache`.
  - Current validation requires `--disaggregation-transfer-backend nixl` when that flag is set.

## Interface

Enable decode radix cache on the **decode** worker with:

```bash
--disaggregation-mode decode --disaggregation-transfer-backend nixl --disaggregation-decode-enable-radix-cache
```

Prefill continues to run with `--disaggregation-transfer-backend nixl`.

Note: DP attention is still experimental here. The flag is allowed, but good cache hit rates require prefix-aware DP routing.

## Benchmark

### Setup

- **Hardware**: 1x NVIDIA B200 node (8 GPUs), single-node PD disaggregation via NIXL
- **Model**: `Qwen/Qwen3-32B`, FP8 KV cache, 3P1D, TP=2 per worker
- **Workload**: 20 unique ~50K-token prefixes + ~4.5K suffix (~91% prefix reuse), 1000 requests, concurrency 128

### Results

| Metric | Baseline | Decode Radix Cache | Improvement |
|--------|----------|--------------------|-------------|
| Request throughput (req/s) | 1.21 | 1.59 | **1.32x** |
| Output token throughput (tok/s) | 430 | 566 | **1.32x** |
| TTFT p50 (s) | 73.2 | 9.0 | **8.1x** |
| TTFT avg (s) | 77.7 | 31.6 | **2.5x** |
| Request latency p50 (s) | 99.1 | 73.4 | **1.35x** |
| ITL avg (ms) | 65.6 | 130.6 | 0.50x |
| Benchmark duration (s) | 827 | 628 | **1.32x** |

Decode-side logs show the reason for the throughput gain: baseline decode ran near KV capacity (`token_usage ~ 0.99`) and only fit ~37 running requests, while decode radix cache reduced duplicate prefix residency (`token_usage ~ 0.75`) and fit roughly 104-126 running requests. The ITL regression is expected from the larger decode batch.

## Test Plan

- [x] Qwen3-0.6B local PD disagg sanity runs
- [x] MiniMax-M2.5 1P1D on B200
- [x] Qwen3-32B 3P1D on B200 (results above)
- [x] Guard decode radix cache behind `nixl` in `server_args.py`
- [ ] Multi-node cross-host testing (RDMA transport)
- [ ] Mooncake transfer backend support (separate PR)
