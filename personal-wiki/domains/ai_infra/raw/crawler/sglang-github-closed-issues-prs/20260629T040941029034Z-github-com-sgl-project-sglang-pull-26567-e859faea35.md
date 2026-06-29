---
source_id: sglang-github-closed-issues-prs
title: Speed up DeepGEMM JIT warmup with per-PP-rank parallel compile
canonical_url: https://github.com/sgl-project/sglang/pull/26567
captured_at: '2026-06-29T04:09:41.029034+00:00'
content_hash: e859faea35d38d83f676e6049b62207405945e4fbc864b2188679003d901b1b7
---
# Speed up DeepGEMM JIT warmup with per-PP-rank parallel compile

URL: https://github.com/sgl-project/sglang/pull/26567
State: closed
Labels: run-ci
Closed at: 2026-06-02T02:51:27Z
Merged at: 2026-06-02T02:51:27Z

## Summary

Parallelize DeepGEMM JIT kernel compilation across PP ranks during startup warmup.

## Motivation

Today the startup warmup /generate request flows through PP stages serially: stage k can only start its DeepGEMM JIT compile after stage k-1 finishes. For large MoE models like DeepSeek-V4 this dominates startup time.

## Change

Add a per-PP-rank local dummy forward inside ModelRunner.kernel_warmup(). Each scheduler process is independent, so all PP ranks now trigger their layers' DeepGEMM JIT compile concurrently.

- New _pp_parallel_deep_gemm_warmup() runs _dummy_run(DECODE) + _dummy_run(EXTEND) with batch_size=1, gated on pp_size > 1, ENABLE_JIT_DEEPGEMM, non-speculative. Wrapped in try/except for graceful fallback.
- Extend _dummy_run with forward_mode_override so a generation model can also exercise EXTEND-mode shapes (CONTIG grouped GEMM); extend-buffer setup gate switched from not is_generation to capture_forward_mode == EXTEND, semantically equivalent for all existing callers.
- Pass hc_hidden_size to DecodeInputBuffers.create in _dummy_run so DSv4 mHC PP IPC buffer is allocated correctly (parity with cuda_graph_runner).

to enable this feauture:   set  `SGLANG_PP_PARALLEL_DEEPGEMM_WARMUP=1`
## Result

On H20 with DeepSeek-V4-Pro --pp 4 --tp 8:

with prebuit cache:

| CP  | Enable SGLANG_PP_PARALLEL_DEEPGEMM_WARMUP | startup time     | 
|-----|-----------------|--------------|
| OFF | OFF             | ~9 min      |
| OFF | ON              | ~3 min 40s   |
| ON  | OFF             | ~12 min      |
| ON  | ON              | ~4 min 4 s   |

CC  @ShangmingCai @Fridge003 






























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #26715451885](https://github.com/sgl-project/sglang/actions/runs/26715451885)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #26715451816](https://github.com/sgl-project/sglang/actions/runs/26715451816)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
