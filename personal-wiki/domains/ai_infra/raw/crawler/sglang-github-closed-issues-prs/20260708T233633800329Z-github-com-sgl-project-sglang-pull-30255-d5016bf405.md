---
source_id: sglang-github-closed-issues-prs
title: Fix DSV4 prefill large Triton recompilation idle across context lengths
canonical_url: https://github.com/sgl-project/sglang/pull/30255
captured_at: '2026-07-08T23:36:33.800329+00:00'
content_hash: d5016bf405c3548a5737b0bbd4dc5ecab19dbfa5b2e6a7d3a52717366a03820d
---
# Fix DSV4 prefill large Triton recompilation idle across context lengths

URL: https://github.com/sgl-project/sglang/pull/30255
State: closed
Labels: run-ci
Closed at: 2026-07-08T03:35:33Z
Merged at: 2026-07-08T03:35:33Z

## Motivation

DeepSeek-V4 sparse prefill derives the C128 metadata capacity and sparse-index combiner top-k from the live context length. Both values were passed to Triton as `tl.constexpr`, so changing an exact context length generated a new kernel specialization. These synchronous JIT compilations introduce huge stalling.

## Modifications

- Pass the exact C128 metadata capacity as a runtime scalar and iterate over it with a masked `tl.range`.
- Pass the sparse combiner's exact `top_k` as a runtime scalar.
- Remove the unused private metadata-kernel `page_size` argument.

## Speed Tests and Profiling

AgentX benchmark concurrency 384 shows great perf improvement.

| Metric | Baseline | This PR | Delta |
|---|---:|---:|---:|
| Mean TTFT | 32.682 s | 20.836 s | -36.25% |
| Output throughput | 10,423.36 tok/s | 13,211.38 tok/s | +26.75% |
| Input throughput | 1,444,106.37 tok/s | 1,771,722.55 tok/s | +22.69% |
| Request throughput | 10.67 req/s | 13.74 req/s | +28.74% |
| Mean ITL | 14.300 ms | 15.670 ms | +9.58% |

The kernel perf won't regress by reduced specialization:

Direct steady-state kernel benchmarks on the same GB300 allocation (`warmup=100`, `rep=500`) found no meaningful regression:

| Kernel | Shape | Baseline | This PR | Delta |
|---|---|---:|---:|---:|
| C128 metadata | `bs=4096`, `max_pages=2048` | 0.0711253 ms | 0.0703080 ms | -1.15% |
| Sparse combiner | `num_tokens=4096`, `top_k=4084` | 0.0607069 ms | 0.0610846 ms | +0.62% |

An additional same-GPU, alternating metadata sweep at `max_pages=512` also found no meaningful regression:

| Batch size | Baseline | This PR | Delta |
|---:|---:|---:|---:|
| 1 | 32.256 µs | 29.600 µs | -8.23% |
| 32 | 29.088 µs | 29.552 µs | +1.60% |
| 256 | 32.560 µs | 30.416 µs | -6.58% |

## Accuracy Tests

A full 5-shot GSM8K evaluation on the patched version achieved 1,274/1,319 strict-match accuracy (96.59%)































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28846608165](https://github.com/sgl-project/sglang/actions/runs/28846608165)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28846608089](https://github.com/sgl-project/sglang/actions/runs/28846608089)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
