---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Add M-aware fp8 block-scale GEMM dispatch in dpsk-v4'
canonical_url: https://github.com/sgl-project/sglang/pull/27594
captured_at: '2026-07-07T23:35:30.905531+00:00'
content_hash: 2c0c3cb36085fa36b96faa39c5e1955866b99e813e8e4adb560bb35f2aaf8b57
---
# [AMD] Add M-aware fp8 block-scale GEMM dispatch in dpsk-v4

URL: https://github.com/sgl-project/sglang/pull/27594
State: closed
Labels: deepseek, jit-kernel
Closed at: 2026-06-25T03:33:00Z
Merged at: 

## Motivation

Speed up DeepSeek-V4 dense-GEMM prefill on the AMD gfx950 (MI350X/MI355X) code path without touching decode or accuracy.

At prefill-scale M, the decode/small-M-tuned triton allowlist is a net loss (microbenchmarks showed they were slower than non-preshuffle CK) for two dense projection shapes. We reroute them to the aiter non-preshuffle CK block-scale GEMM. The change only applies to large prefill GEMMs; decode, small-M, and CUDA-graph paths are unchanged. This provides ~1-2% TTFT improvement at low conc and onpar with baseline at high conc.

## Modifications

**M-aware FP8 GEMM dispatch (gfx950)**
- File: `python/sglang/srt/layers/quantization/fp8_utils.py`
- In `aiter_w8a8_block_fp8_linear`, the allowlist shapes `{(7168, 2048), (4096, 7168)}` (which the tuned-triton allowlist would otherwise pick) are rerouted to the aiter non-preshuffle `ck_gemm_a8w8_blockscale` when `m >= 1024` (`_AITER_TRITON_TO_CK_LARGE_M_GFX950 = 1024`).
- The reroute applies at all tensor-parallel and data-parallel configurations; non-preshuffle CK is faster than tuned-triton on these shapes at all M at or above the threshold (including the ~1024 per-rank M under data-parallel attention).
- Decode / small-M (M < 1024) is untouched. Layout-safe: `fp8.py` leaves the allowlist weights **unshuffled**, which is exactly what non-preshuffle CK consumes.

## Accuracy Tests

gsm8k (1319 q, 8-shot, parallel=200, temp=0.01):

| | accuracy | gate (>0.92) |
|---|---:|---|
| M-aware dispatch | 0.957 | PASS |

The reroute runs the same fp8 block-scale math through a different kernel, so numerics are unchanged.

## Speed Tests and Profiling

MI350X, random input 8192 / output 1024. Median TTFT (ms). Ratio = base / ours; > 1.00 = ours faster.

Server cmd:
```
export SGLANG_DEFAULT_THINKING=1
export SGLANG_DSV4_REASONING_EFFORT=max
export SGLANG_OPT_DEEPGEMM_HC_PRENORM=false
export SGLANG_USE_AITER=1
export SGLANG_USE_ROCM700A=1
export SGLANG_OPT_USE_FUSED_COMPRESS=true
# export SGLANG_HACK_FLASHMLA_BACKEND=triton
export SGLANG_HACK_FLASHMLA_BACKEND=unified_kv_triton
export SGLANG_OPT_FP8_WO_A_GEMM=false
export SGLANG_OPT_USE_JIT_INDEXER_METADATA=false
export SGLANG_OPT_USE_TOPK_V2=false
export SGLANG_OPT_USE_AITER_INDEXER=true
export SGLANG_OPT_USE_TILELANG_INDEXER=false
export SGLANG_OPT_USE_TILELANG_MHC_PRE=false
export SGLANG_OPT_USE_TILELANG_MHC_POST=false
export SGLANG_FP8_PAGED_MQA_LOGITS_TORCH=1
export SGLANG_OPT_USE_FUSED_COMPRESS_TRITON=true

export SGLANG_OPT_USE_MULTI_STREAM_OVERLAP=false
export SGLANG_ROCM_USE_MULTI_STREAM=false

export AITER_BF16_FP8_MOE_BOUND=0

# --dp 8 --enable-dp-attention \
# --speculative-algorithm EAGLE --speculative-num-steps 3 --speculative-num-draft-tokens 4 --speculative-eagle-topk 1
# --disable-cuda-graph \
MODEL=/data/deepseek-ai/DeepSeek-V4-Pro
sglang serve \
    --model-path ${MODEL} \
    --trust-remote-code \
    --tp 8 \
    --disable-radix-cache \
    --attention-backend dsv4 \
    --max-running-request 256 \
    --page-size 256 \
    --mem-fraction-static 0.90 \
    --swa-full-tokens-ratio 0.1 \
    --chunked-prefill-size 8192 \
    --port 8000 \
    --disable-shared-experts-fusion \
    --tool-call-parser deepseekv4 \
    --reasoning-parser deepseek-v4
```

Client cmd:
```
python3 -m sglang.bench_serving --host localhost --port 8000 --dataset-name random --random-input 8192 --random-output 1024 --random-range-ratio 1.0 --num-prompt {cc*4} --max-concurrency {cc}
```

Base: low-conc = same-box MI350X baseline (M-aware override off); high-conc = same-box MI350X `main`. Decode path is untouched, so TPOT stays at parity.

**Low concurrency (TP8 / DP1)** — base is same-box MI350X baseline (M-aware override off):

| Concurrency | TP, DP | Median TTFT ours (ms) | Median TTFT base (ms) | TTFT | Median TPOT ours (ms) | Median TPOT base (ms) |
|---:|:---:|---:|---:|---:|---:|---:|
| 2 | 8, 1 | 596.51 | 603.23 | 1.01 | 16.01 | 15.95 |
| 4 | 8, 1 | 1006.50 | 1018.62 | 1.01 | 16.45 | 16.42 |
| 8 | 8, 1 | 1880.30 | 1904.99 | 1.01 | 18.16 | 18.13 |
| 16 | 8, 1 | 3264.85 | 3317.29 | 1.02 | 21.94 | 21.94 |

**High concurrency (TP8 / DP8)** — base is MI350X `main` branch:

| Concurrency | TP, DP | Median TTFT ours (ms) | Median TTFT base (ms) | TTFT | Median TPOT ours (ms) | Median TPOT base (ms) |
|---:|:---:|---:|---:|---:|---:|---:|
| 32 | 8, 8 | 5437.28 | 5439 | 1.00 | 30.82 | 30.84 |
| 64 | 8, 8 | 8544.35 | 8554 | 1.00 | 40.85 | 40.76 |

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Files changed

- `python/sglang/srt/layers/quantization/fp8_utils.py` — M-aware dispatch (reroute allowlist shapes triton -> non-preshuffle CK at M >= 1024).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #27283248114](https://github.com/sgl-project/sglang/actions/runs/27283248114)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27283247047](https://github.com/sgl-project/sglang/actions/runs/27283247047)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
