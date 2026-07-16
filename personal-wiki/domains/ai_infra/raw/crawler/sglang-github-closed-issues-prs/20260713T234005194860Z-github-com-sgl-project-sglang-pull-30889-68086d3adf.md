---
source_id: sglang-github-closed-issues-prs
title: 'feat: enable piecewise prefill graph for Kimi K2.5/K2.7'
canonical_url: https://github.com/sgl-project/sglang/pull/30889
captured_at: '2026-07-13T23:40:05.194860+00:00'
content_hash: 68086d3adf4d182290c0007bf1d233378443e0ca9f82da094d0298c17859cf7a
---
# feat: enable piecewise prefill graph for Kimi K2.5/K2.7

URL: https://github.com/sgl-project/sglang/pull/30889
State: closed
Labels: Multi-modal, run-ci
Closed at: 2026-07-13T00:37:30Z
Merged at: 2026-07-13T00:37:30Z

## Summary

- opt `KimiK25ForConditionalGeneration` into multimodal `tc_piecewise` prefill CUDA graph
- upgrade the default CUDA prefill backend from incompatible `breakable` to `tc_piecewise` for validated multimodal models only
- retain eager vision encoding: only the LM prefill forward is captured
- add a CPU regression test so unsupported multimodal architectures remain opted out

## Validation

- CPU: `PYTHONPATH=python python3 -m pytest test/registered/unit/configs/test_multimodal_piecewise_cuda_graph.py -q` — **3 passed**.
- NVIDIA H200 TP8, `moonshotai/Kimi-K2.7-Code`, native compressed-tensors int4, FA3 for LM and vision, DP MM encoder, CUDA IPC enabled:
  - candidate PR automatically resolved to `prefill.backend=tc_piecewise` with no explicit CUDA-graph flag
  - captured 42 prefill sizes (4…2048) in 109.39s, using 1.33 GiB additional memory per GPU
  - server passed `/health` and completed the seeded random-image r1/r8/r32 matrix
  - K2.7 TP8 eager itself is not token-exact across repeated int4 runs (5/16 short prefixes differ); PCG repeats differ 3/16, so this manual validation checks service health and output behavior rather than claiming token-exact equality

## Performance (before → after)

Strict A/B on one NVIDIA H200 TP8 host: `origin/main` `32cb89d` versus this PR `f3d3195`; native compressed-tensors int4, FA3 LM/vision attention, DP MM encoder, CUDA IPC enabled, radix cache disabled. The seeded `bench_serving` trace contains 16 requests, one random JPEG each, `random:256x256-1024x1024`, 32 text input tokens, and 16 output tokens. Each rate has its own one-request warmup. `r32` uses the repeat result for the PCG side.

| Request rate | Output tok/s (main → PCG) | TTFT p50 / p99 ms (main → PCG) | E2E p50 / p99 ms (main → PCG) |
| --- | ---: | ---: | ---: |
| 1/s | 13.34 → 13.34 (0.0%) | 140 / 273 → 96 / 152 (-31% / -44%) | 215 / 351 → 160 / 242 (-26% / -31%) |
| 8/s | 85.92 → 95.85 (+11.5%) | 476 / 896 → 153 / 255 (-68% / -72%) | 760 / 1029 → 496 / 1194 (-35% / +16%) |
| 32/s | 139.61 → 142.75 (+2.3%) | 641 / 782 → 589 / 712 (-8% / -9%) | 830 / 1012 → 806 / 988 (-3% / -2%) |

PCG resolves the incompatible default (`breakable` disables MLA prefill graphs) and moves heterogeneous-shape capture to startup. The explicit cost is the 109.39s / 1.33 GiB-per-GPU capture noted above. At 8/s, the first high-concurrency eager shape stalls materially; PCG removes that stall, but its E2E p99 is still worse in this small trace. Thus this PR improves the documented cold-shape and median-latency path, but does not claim to solve every saturated-tail bottleneck.

This measurement still has the known TileLang CUDA-runtime-stub issue, which disables SGLang FlashInfer all-reduce fusion. That dependency issue is separate and leaves the high-load SGLang/vLLM gap conservative.















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29160274313](https://github.com/sgl-project/sglang/actions/runs/29160274313)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29160842701](https://github.com/sgl-project/sglang/actions/runs/29160842701)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
