---
source_id: sglang-github-closed-issues-prs
title: '[AMD] [GLM5] Fuse DSA indexer query Hadamard + FP8 quant (gfx950)'
canonical_url: https://github.com/sgl-project/sglang/pull/29437
captured_at: '2026-07-05T02:14:10.239172+00:00'
content_hash: 0ebd621b838848f4656e6d3421a49015dc0d0302f1bbfa3050f977b0700aa192
---
# [AMD] [GLM5] Fuse DSA indexer query Hadamard + FP8 quant (gfx950)

URL: https://github.com/sgl-project/sglang/pull/29437
State: closed
Labels: quant
Closed at: 2026-07-04T18:54:42Z
Merged at: 

## Motivation

The DSA indexer issues many tiny per-layer kernels (~4µs each: qk-rmsnorm, rope+cache, fp8 quant, Hadamard, top-k). On gfx950 these run serially (no multi-stream overlap), so per-kernel launch overhead and under-occupied launches dominate the indexer's wall-time. This fuses adjacent query-side ops to cut the launch count.

## Modifications

Fuse the indexer query's **Hadamard transform + block FP8 quant** into a single Triton kernel (`fused_hadamard_act_quant`), replacing the two-pass `act_quant(rotate_activation(q))` which writes a bf16 tensor to HBM then reads it back. The fused kernel keeps the post-Hadamard row in registers and quantizes in place, removing one bf16 HBM round-trip of the query per layer.

On the decode path, the same kernel also folds **`_apply_q_scale_and_softmax_scale`** (`weights * q_scale * softmax_scale`): the kernel already emits `q_scale`, and the head-gate `weights` are row-aligned and ready before the quant, so the per-(token,head) rescale is emitted as an extra output instead of a separate elementwise launch (`triton_poi_fused_mul_unsqueeze`).

- Opt-in, shape-guarded: `SGLANG_DSA_FUSE_HADAMARD_QUANT=1`, gfx950, `head_dim == block_size == 128`; default off, two-pass path unchanged. Query-only.
- Hadamard = matmul vs the ±1 Sylvester matrix (fp32 accum) ×`1/sqrt(N)`, equivalent to `fast_hadamard_transform(x, scale=N**-0.5)`. Quant matches `act_quant` (group=128 absmax, e4m3fn + fp32 scale).

## Accuracy Tests

GLM-5.1-MXFP4, MI355X TP4, GSM8K (1319 questions):

| config | GSM8K |
|---|---|
| fusion on | 0.938 |

Numerically equivalent to the two-pass path: the fp8 output agrees to within 1 ULP, and the folded `weights * q_scale * softmax_scale` is bit-exact vs `_apply_q_scale_and_softmax_scale`. Matches the GLM-5.1-MXFP4 baseline.

## Speed Benchmarks

GLM-5.1-MXFP4, MI355X TP4, graphs-on, random 8192/512, `sglang.bench_serving`, median.

Baseline (fusion off):

| concurrency | TTFT (ms) | TPOT (ms) | E2EL (ms) |
|---|---|---|---|
| 4  | 1616.69  | 22.53 | 13029.63 |
| 8  | 2667.60  | 26.50 | 16241.42 |
| 16 | 4737.31  | 34.08 | 22163.20 |
| 32 | 8899.95  | 46.72 | 32786.16 |
| 64 | 17356.27 | 69.54 | 52926.13 |

Fusion on (Δ vs baseline):

| concurrency | TTFT (ms) | TPOT (ms) | E2EL (ms) |
|---|---|---|---|
| 4  | 1596.57 (−1.24%)  | 22.31 (−0.98%) | 12996.50 (−0.25%) |
| 8  | 2628.63 (−1.46%)  | 26.27 (−0.87%) | 16052.06 (−1.17%) |
| 16 | 4652.54 (−1.79%)  | 33.88 (−0.59%) | 21980.28 (−0.83%) |
| 32 | 8771.57 (−1.44%)  | 46.11 (−1.31%) | 32383.37 (−1.23%) |
| 64 | 16943.11 (−2.38%) | 69.12 (−0.60%) | 52261.78 (−1.26%) |

## Checklist

- [x] Format your code according to the Format code with pre-commit.
- [ ] Add unit tests according to the Run and add unit tests.
- [ ] Update documentation according to Write documentations.
- [x] Provide accuracy and speed benchmark results.
- [x] Follow the SGLang code style guidance.

## Review and Merge Process

1. Ping Merge Oncalls to start the process.
2. Get approvals from CODEOWNERS and other reviewers.
3. Trigger CI tests with comments.
