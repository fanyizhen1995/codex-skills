---
source_id: sglang-github-closed-issues-prs
title: '[DeepSeek-V4] Add an opt-in non-paged indexer for long-context prefill'
canonical_url: https://github.com/sgl-project/sglang/pull/29619
captured_at: '2026-07-07T23:35:30.913255+00:00'
content_hash: 8f3bc00a63f07b8833d803fa84a4dae752d611db807e5f056592407ea8fcb8bb
---
# [DeepSeek-V4] Add an opt-in non-paged indexer for long-context prefill

URL: https://github.com/sgl-project/sglang/pull/29619
State: closed
Labels: deepseek, run-ci, release-highlight
Closed at: 2026-07-03T05:54:41Z
Merged at: 2026-07-03T05:54:41Z

## Motivation

DeepSeek-V4's C4 indexer currently evaluates logits directly from paged KV storage. For long-context, unpadded single-request `EXTEND` batches, gathering the C4 index keys and scales into contiguous storage enables the faster non-paged DeepGEMM `fp8_mqa_logits` path while preserving the existing top-k semantics.

This PR adds that path behind a default-off environment flag.

Related to #23602.

## Modifications

- Add a default-off non-paged C4 indexer path for eligible single-request, unpadded `EXTEND` batches.
- Reuse one validated gather plan across indexer layers and fall back to the existing paged path for unsupported inputs, backends, or graph modes.
- Add focused CPU tests for eligibility, plan geometry, extreme-size fail-closed behavior, and the gather/dispatch contract.

## Accuracy Tests

```bash
pip install git+https://github.com/sgl-project/sgl-eval

sgl-eval run gsm8k \
  --model deepseek-ai/DeepSeek-V4-Pro --api-key <api-key> \
  --n-repeats 1 --temperature 1.0 --top-p 0.95 --no-thinking \
  --out-dir /sgl-workspace/logs \
  --base-url http://localhost:30000/v1

sgl-eval run aime25 \
  --model deepseek-ai/DeepSeek-V4-Pro --api-key <api-key> \
  --n-repeats 16 --max-tokens 400000 \
  --temperature 1.0 --top-p 1.0 --thinking \
  --out-dir /sgl-workspace/logs \
  --base-url http://localhost:30000/v1
```

| Evaluation | Result |
|---|---:|
| GSM8K | 96.59% (1,274 / 1,319; 0% error, 0% truncated) |
| AIME25 pass@1 (average of 16 repeats) | 99.17% (476 / 480; pass@16 100%; majority@16 100%; 2 errors, 0 truncated) |

## Speed Tests and Profiling

### End-to-end experiment

The treatment prefill worker used the following configuration; the baseline used the same command with `SGLANG_OPT_DSV4_NONPAGED_INDEXER=0`.

```bash
SGLANG_OPT_DSV4_NONPAGED_INDEXER=1 \
SGLANG_RADIX_FORCE_MISS=1 \
python3 -m sglang.launch_server \
  --model deepseek-ai/DeepSeek-V4-Pro \
  --trust-remote-code \
  --disaggregation-mode prefill \
  --disaggregation-transfer-backend mooncake \
  --tp 4 --dp 4 --ep 4 \
  --enable-dp-attention --enable-dp-lm-head \
  --moe-a2a-backend deepep \
  --kv-cache-dtype fp8_e4m3 \
  --mem-fraction-static 0.9 \
  --max-running-requests 128 \
  --cuda-graph-max-bs 128 \
  --chunked-prefill-size 32768 \
  --context-length 262144 \
  --disable-flashinfer-autotune
```

Workload: fixed nominal-128K input, output length 1, concurrency 8, and server-side full-chunk prefill throughput over a fixed 300-second window.

| Pair | Order / placement | Baseline median (tok/s/rank) | Non-paged median (tok/s/rank) | Pooled median gain | Rank-equal gain |
|---|---|---:|---:|---:|---:|
| 1 | baseline -> treatment | 12,188.145 | 12,465.880 | +2.279% | +2.210% |
| 2 | treatment -> baseline | 11,940.050 | 12,555.300 | +5.153% | +5.380% |
| 3 | same placement, baseline -> treatment | 11,576.590 | 12,330.800 | +6.515% | +6.451% |
| Final PR head `eb08e8d517` | same placement, baseline -> treatment | 12,001.005 | 12,318.740 | +2.648% | +2.708% |

The equal-weight aggregate across the 3 prototype pairs x 4 DP ranks was **+4.665%**, with all **12/12 per-rank effects positive**. The exact clean PR head was then rerun as a same-placement serial pair: rank-equal gain was **+2.708%**, pooled-median gain was **+2.648%**, and all **4/4 DP-rank effects were positive** (`+4.089% / +1.273% / +4.251% / +1.258%`). Both arms used the same source, workload/configuration, and fixed 300-second analysis contract; the feature flag was the treatment difference. This single final-head pair validates direction but is not a stable-magnitude or default-on claim.

### Kernel microbenchmark

| Original context | Net indexer latency reduction, including gather |
|---:|---:|
| 32K | 19.1% |
| 64K | 26.6% |
| 128K | 23.0% |

At 128K:

| Paged logits | Gather | Non-paged logits | Gather + non-paged | Net change |
|---:|---:|---:|---:|---:|
| 2,870.2 us | 104.0 us | 2,105.1 us | 2,209.1 us | -23.0% |

### Kernel Breakdown

  Setup: 1× GB300 node (4 GPUs), TP4/DP4/EP4 with DP attention and FP8 KV cache. Fixed 128K ISL, OSL=1, concurrency=32, and an 8,192-token prefill chunk per rank; cache reuse was disabled.

  Across 480 matched indexer-layer calls, the replaced GPU span decreased from 1.524 ms to 1.068 ms at p50, with a 29.9% reduction by paired totals.

Before:
sm100_fp8_paged_mqa_logits (1.522 ms)
<img width="2768" height="266" alt="image" src="https://github.com/user-attachments/assets/795ad6f1-3504-45b5-9ea1-937d0b84c11d" />

After:
_get_k_and_s_triton_kernel + deep_gemm::sm100_fp8_mqa_logits ( <1ms)
<img width="2874" height="246" alt="image" src="https://github.com/user-attachments/assets/d0831b8b-10d5-4800-874a-d8f5bbe44174" />
<img width="1408" height="234" alt="image" src="https://github.com/user-attachments/assets/3bb16d52-1302-48de-a688-80e4abe3e63a" />


## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.





















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28550494176](https://github.com/sgl-project/sglang/actions/runs/28550494176)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:hourglass_flowing_sand: [Run #28853485756](https://github.com/sgl-project/sglang/actions/runs/28853485756)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
