---
source_id: sglang-github-closed-issues-prs
title: '[AMD] [GLM5] Route DSA indexer q/k RoPE through apply_rope_inplace on gfx950'
canonical_url: https://github.com/sgl-project/sglang/pull/30195
captured_at: '2026-07-08T23:36:33.786962+00:00'
content_hash: f9f6b20271276642bbce7511ce635bd5911c720c27739cbb68e9959b83474978
---
# [AMD] [GLM5] Route DSA indexer q/k RoPE through apply_rope_inplace on gfx950

URL: https://github.com/sgl-project/sglang/pull/30195
State: closed
Labels: jit-kernel
Closed at: 2026-07-08T03:17:58Z
Merged at: 

## Motivation

On gfx950 the DSA indexer applies RoPE to its q/k through aiter's cached-position
kernel (`kn_entry_2c_sbhd_cached_indirect_inplace`). This adds an opt-in path
that instead routes the indexer q/k rope through the portable
`apply_rope_inplace` kernel already used on the CUDA path, which is faster for
the indexer's small q/k shapes.

## Modifications

Add `SGLANG_DSA_FUSED_ROPE=1` (gfx950 only, default off): route the indexer q/k
rope through `jit_kernel/rope.py`'s `apply_rope_inplace`, for both
`_get_q_k_bf16` and `_get_k_bf16`. Supports the GLM-5.2 interleaved
(`is_neox=False`) layout.

## Accuracy Tests

GLM-5.2-MXFP4, MI355X TP4, GSM8K (1319 questions):

| config | GSM8K |
|---|---|
| baseline | 0.925 |
| fused-rope on | 0.936 |

## Speed Benchmarks

GLM-5.2-MXFP4, MI355X TP4, graphs-on, random 8192/1024, `sglang.bench_serving`, median.

Baseline:

| concurrency | TTFT (ms) | TPOT (ms) | E2EL (ms) |
|---|---|---|---|
| 2  | 661   | 14.00 | 15332 |
| 4  | 1412  | 14.58 | 16600 |
| 8  | 2024  | 16.41 | 20231 |
| 16 | 3543  | 19.48 | 26342 |
| 32 | 6627  | 22.99 | 36047 |
| 64 | 13058 | 29.02 | 55110 |

Fused-rope on:

| concurrency | TTFT (ms) | TPOT (ms) | Δ TPOT | E2EL (ms) | Δ E2EL |
|---|---|---|---|---|---|
| 2  | 652   | 13.90 | −0.71% | 15157 | −1.14% |
| 4  | 1231  | 14.48 | −0.69% | 16502 | −0.59% |
| 8  | 2005  | 16.24 | −1.04% | 19880 | −1.73% |
| 16 | 3589  | 19.32 | −0.82% | 26164 | −0.68% |
| 32 | 6633  | 22.80 | −0.83% | 36048 | −0.00% |
| 64 | 12850 | 28.81 | −0.72% | 54391 | −1.30% |

## Checklist

- [x] Format the code with pre-commit.
- [x] Accuracy results provided (GSM8K above).
- [x] e2e benchmark results provided (above).

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28764575913](https://github.com/sgl-project/sglang/actions/runs/28764575913)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28764575795](https://github.com/sgl-project/sglang/actions/runs/28764575795)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
