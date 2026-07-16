---
source_id: sglang-github-closed-issues-prs
title: Preserve SWA sliding-window suffix during eviction
canonical_url: https://github.com/sgl-project/sglang/pull/26907
captured_at: '2026-07-13T23:40:05.193611+00:00'
content_hash: 83ec1c747ce44b4d93ec5d0507c10b91b9ff599d3d359921373955938a8eaa57
---
# Preserve SWA sliding-window suffix during eviction

URL: https://github.com/sgl-project/sglang/pull/26907
State: closed
Labels: high priority, run-ci
Closed at: 2026-07-13T02:56:15Z
Merged at: 

## Summary
- Implement window cache retain in https://github.com/sgl-project/sglang/issues/26577
- add an LRU-position-preserving split mode for UnifiedRadixCache nodes
- make SWA device eviction trim internal nodes to a page-aligned trailing sliding-window suffix before evicting retained windows under continued pressure
- add defensive locked-node handling and unit coverage for retention splits, LRU ordering, second-pass eviction, SWA+Mamba state, and host-backed SWA state

## Notes
- By default, SGLANG_SWA_CACHE_CHECKPOINT_MIN_TOKEN_INTERVAL=0 skips the SWA checkpoint soft pass and keeps dense eviction behavior. Set it to -1 for structural checkpoints only or a positive token interval to retain sparse trailing window checkpoints; under continued pressure, the second pass may still evict retained windows and D-leaves.

## Perf

SA agent bench, DSV4 GB300, 1P/1D, C30, HiCache off.

| SWA ratio | Variant | Cache hit | Output tok/s | TTFT p90 |
|---:|---|---:|---:|---:|
| 0.007 | Baseline | 2.46% | 203.23 | 175.90s |
| 0.007 | This PR, `SGLANG_SWA_CACHE_CHECKPOINT_MIN_TOKEN_INTERVAL=81920` | 13.00% | 220.83 | 166.06s |
| 0.015 | Baseline | 8.18% | 206.67 | 163.55s |
| 0.015 | This PR, `SGLANG_SWA_CACHE_CHECKPOINT_MIN_TOKEN_INTERVAL=81920` | 94.49% | 833.02 | 5.68s |
| 0.015 | This PR, `SGLANG_SWA_CACHE_CHECKPOINT_MIN_TOKEN_INTERVAL=-1` | 89.36% | 706.04 | 21.25s |
| 0.020 | Baseline | 8.40% | 213.56 | 165.61s |
| 0.020 | This PR, `SGLANG_SWA_CACHE_CHECKPOINT_MIN_TOKEN_INTERVAL=81920` | 94.68% | 821.43 | 6.08s |
| 0.020 | This PR, `SGLANG_SWA_CACHE_CHECKPOINT_MIN_TOKEN_INTERVAL=0` | 7.67% | 212.96 | 169.50s |

SA agent bench, DSV4 GB300, 3P/1D, C500, HiCache on.

| SWA ratio | Variant | Cache hit | Output tok/s | TTFT p90 |
|---:|---|---:|---:|---:|
| 0.01 | Baseline | 89.47% | 5,216.81 | 127.55s |
| 0.01 | This PR, `SGLANG_SWA_CACHE_CHECKPOINT_MIN_TOKEN_INTERVAL=81920` | 92.19% | 6,488.80 | 91.53s |

AA agent bench, DSV4 GB300, 3P/1D, HiCache on 

This PR:
| swa ratio | cache hit | server out tok/s | TTFT p50 / p95 / p99 | SSE p25 | latest full dev | latest SWA dev | latest full host | latest SWA host |
|----------:|----------:|-----------------:|----------------------|--------:|----------------:|---------------:|-----------------:|----------------:|
| 0.01      | 93.70%    | 4069.9           | 6.120 / 11.980 / 15.007s | 54.96 | 99.7%           | 82.3%          | 66.9%           | 100.0%          |
| 0.04      | 94.82%    | 4538.1           | 4.824 / 9.380 / 11.434s  | 53.09 | 99.6%           | 94.4%          | 96.4%           | 100.0%          |
| 0.05      | 94.81%    | 4444.9           | 5.200 / 9.849 / 15.965s  | 53.34 | 99.7%           | 95.7%          | 100.0%          | 100.0%          |
| 0.10      | 93.46%    | 3037.9           | 11.356 / 20.024 / 24.880s| 59.62 | 99.6%           | 68.2%          | 100.0%          | 99.7%           |

baseline:
| swa ratio | cache hit | server out tok/s | TTFT p50 / p95 / p99 | SSE p25 |
|----------:|----------:|-----------------:|----------------------|--------:|
| 0.04      | 93.8%     | 3035.1           | 3.398s / 9.569s / 12.584s | 56.8 |

And swa 0.01 in baseline just failed for OOM.













































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28492124587](https://github.com/sgl-project/sglang/actions/runs/28492124587)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28492124517](https://github.com/sgl-project/sglang/actions/runs/28492124517)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
