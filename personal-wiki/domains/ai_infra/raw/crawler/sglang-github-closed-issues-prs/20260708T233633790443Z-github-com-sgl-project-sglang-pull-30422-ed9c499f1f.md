---
source_id: sglang-github-closed-issues-prs
title: '[AMD] [GLM5] Fuse DSA indexer q/k rope+norm+quant+cache-store into one aiter
  kernel (gfx950)'
canonical_url: https://github.com/sgl-project/sglang/pull/30422
captured_at: '2026-07-08T23:36:33.790443+00:00'
content_hash: ed9c499f1f3dfadd180dd6923d86af76ca975c092caf94aba8892f6a40982f6f
---
# [AMD] [GLM5] Fuse DSA indexer q/k rope+norm+quant+cache-store into one aiter kernel (gfx950)

URL: https://github.com/sgl-project/sglang/pull/30422
State: closed
Labels: 
Closed at: 2026-07-08T17:10:41Z
Merged at: 

## Motivation

On gfx950 (MI355X) the DSA indexer prepares its q/k through separate launches —
RoPE, k-norm, FP8 activation quant, and the index-K cache store. This fuses them
into a single aiter kernel (`indexer_qk_rope_quant_and_cache`) on the eager
extend/prefill path.

## Modifications

Add `SGLANG_DSA_FUSE_INDEXER_QK=1` (gfx950 only, default off). On the eager
extend/prefill path (not CUDA-graph decode/verify/draft, dual-stream, CP, LoRA,
or quantized-tuple `x`), route the indexer q/k prepare+store through aiter's
`indexer_qk_rope_quant_and_cache`, fusing q/k RoPE + k-norm + FP8 quant + index-K
cache store into one kernel. cos/sin are reshaped to `[max_pos, rope/2]` and moved
to the query device once (the fused path bypasses `rotary_emb.forward`, which
normally migrates them). Graph-captured paths keep the existing fragmented path.
The aiter import is guarded; NVIDIA is unaffected.

This is a prefill-path change; decode-step code is unchanged. The median TPOT
(decode) improvement at high concurrency is therefore a scheduling effect, not a
faster decode step: under continuous batching prefill and decode batches share the
GPU, so shorter prefill reduces the stalls that inflate decode inter-token
latency. It scales with prefill load (negligible for short prompts, ~8% at
8192-token prompts); TTFT stays flat because the indexer is a small fraction of
the prefill.

## Accuracy Tests

amd/GLM-5.2-MXFP4, MI355X (gfx950), TP4, `fp8_e4m3` KV, GSM8K:

| config | GSM8K |
|---|---|
| flag on | 0.943 |

## Speed Benchmarks

amd/GLM-5.2-MXFP4, MI355X (gfx950), TP4, `fp8_e4m3` KV, random 8192/1024,
`sglang.bench_serving`, median, serial single-tenant (low-conc rows are
rep-averaged medians).

Baseline:

| concurrency | TTFT (ms) | TPOT (ms) |
|---|---|---|
| 2  | 646   | 14.34 |
| 4  | 1224  | 15.19 |
| 8  | 2004  | 17.68 |
| 16 | 3547  | 22.23 |
| 32 | 6627  | 28.82 |
| 64 | 13275 | 40.61 |

`SGLANG_DSA_FUSE_INDEXER_QK=1`:

| concurrency | TTFT (ms) | Δ TTFT | TPOT (ms) | Δ TPOT |
|---|---|---|---|---|
| 2  | 657   | +1.7% | 14.19 | −1.0% |
| 4  | 1233  | +0.7% | 14.79 | −2.6% |
| 8  | 2009  | +0.2% | 16.80 | −5.0% |
| 16 | 3571  | +0.7% | 20.39 | −8.3% |
| 32 | 6647  | +0.3% | 26.38 | −8.5% |
| 64 | 13028 | −1.9% | 37.41 | −7.9% |

## Checklist

- [x] Format the code with pre-commit.
- [x] Accuracy evaluation results provided.
- [x] Throughput / latency benchmark results provided.
