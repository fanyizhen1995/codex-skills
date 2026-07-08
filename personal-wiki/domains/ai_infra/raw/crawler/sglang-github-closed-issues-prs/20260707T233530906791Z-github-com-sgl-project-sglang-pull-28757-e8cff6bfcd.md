---
source_id: sglang-github-closed-issues-prs
title: '[AMD] [GLM5] skip redundant -inf pre-fill of HIP indexer MQA-logits'
canonical_url: https://github.com/sgl-project/sglang/pull/28757
captured_at: '2026-07-07T23:35:30.906791+00:00'
content_hash: e8cff6bfcdc193931fc711960f4db8c544748d7bce31a34743432432fdfc65fc
---
# [AMD] [GLM5] skip redundant -inf pre-fill of HIP indexer MQA-logits

URL: https://github.com/sgl-project/sglang/pull/28757
State: closed
Labels: run-ci
Closed at: 2026-06-25T06:21:40Z
Merged at: 2026-06-25T06:21:40Z

## Motivation

This affects HIP serving of DSA (DeepSeek Sparse Attention) models; it was found
and validated on **GLM-5.1-MXFP4** (which uses the DSA indexer) at long context.

On the HIP DSA indexer path, `Indexer._get_topk_ragged` calls aiter's
`fp8_mqa_logits` with the default `clean_logits=True`, which
`torch.full(-inf)`-initializes the `[tokens x seq_len_kv]` logits buffer on every
layer before the kernel writes the valid positions. That pre-fill is **O(seq^2)**
and grows quadratically with context length, so at long context it becomes a
significant share of prefill time (~11% of prefill GPU time at 16x8192 on
gfx950).

The CUDA `deep_gemm.fp8_mqa_logits` path in the same function already passes
`clean_logits=False` and relies on `topk_transform` to mask invalid positions via
`ks`/`ke`/`lengths`. The HIP path simply did not pass the flag, leaving the
redundant fill in place. This aligns the HIP path with CUDA.

## Modifications

- `python/sglang/srt/layers/attention/dsa/dsa_indexer.py`: pass
  `clean_logits=False` to both HIP `fp8_mqa_logits` calls in
  `_get_topk_ragged` (the non-chunked and the budget-chunked branches).
  `topk_transform` already receives the valid per-row range and ignores
  out-of-range positions, so the `-inf` pre-fill is redundant. gfx950 behavior
  is otherwise unchanged; the CUDA path is untouched.

## Accuracy Tests

GSM8K 5-shot, full 1319 questions, GLM-5.1-MXFP4, MI350X (gfx950), tp4,
fp8_e4m3 KV:

| | accuracy | invalid |
|---|---|---|
| before (`clean_logits=True`) | 0.936 | 0.000 |
| after (`clean_logits=False`) | 0.938 | 0.000 |

No regression (delta within run-to-run noise).

## Speed Benchmarks

E2E `sglang.bench_serving` (random, input 8192 / output 1024, median latencies),
GLM-5.1-MXFP4 / MI350X / tp4 / fp8_e4m3 KV:

Baseline (`main`):

| concurrency | total tok/s | TTFT (ms) | ITL (ms) | E2EL (ms) |
|---|---|---|---|---|
| 2 | 938 | 936 | 17.75 | 19664 |
| 4 | 1702 | 1783 | 18.64 | 21627 |
| 8 | 2837 | 2911 | 20.75 | 25916 |
| 16 | 4309 | 5185 | 24.33 | 34222 |
| 32 | 6138 | 9776 | 28.93 | 48123 |
| 64 | 8062 | 18946 | 35.57 | 73134 |

This PR (`clean_logits=False`):

| concurrency | total tok/s | TTFT (ms) | TTFT delta | ITL (ms) | E2EL (ms) |
|---|---|---|---|---|---|
| 2 | 937 | 916 | -2.1% | 17.80 | 19643 |
| 4 | 1703 | 1751 | -1.8% | 18.66 | 21630 |
| 8 | 2820 | 2858 | -1.8% | 20.77 | 26134 |
| 16 | 4298 | 5084 | -1.9% | 24.42 | 34245 |
| 32 | 6223 | 9512 | -2.7% | 28.83 | 47390 |
| 64 | 8174 | 18440 | -2.7% | 35.56 | 72094 |

Median TTFT improves 1.8-2.7% across the sweep; median ITL is unchanged
(within +/-0.5%) and median E2EL is flat-to-slightly-better, confirming the
change is prefill-side with no decode regression. The benefit scales with how
prefill-heavy the workload is (short outputs / RAG / long context).

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.

































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28113605405](https://github.com/sgl-project/sglang/actions/runs/28113605405)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28113605230](https://github.com/sgl-project/sglang/actions/runs/28113605230)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
