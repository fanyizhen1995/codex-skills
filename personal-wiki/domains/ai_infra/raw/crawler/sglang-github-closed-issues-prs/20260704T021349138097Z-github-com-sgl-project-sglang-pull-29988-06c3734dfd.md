---
source_id: sglang-github-closed-issues-prs
title: '[dsv4] Trigger MHC prenorm prewarm at weight-load time with rank sync'
canonical_url: https://github.com/sgl-project/sglang/pull/29988
captured_at: '2026-07-04T02:13:49.138097+00:00'
content_hash: 06c3734dfdd8d292c947f484a1e545bb403aafbee832520e9c2d3999bfc4a1e2
---
# [dsv4] Trigger MHC prenorm prewarm at weight-load time with rank sync

URL: https://github.com/sgl-project/sglang/pull/29988
State: closed
Labels: deepseek
Closed at: 2026-07-03T06:05:04Z
Merged at: 2026-07-03T06:05:03Z

## Motivation

#27986 made the DSV4 MHC prenorm prewarm trigger lazily inside the first forward that carries tokens — per rank, uncoordinated. On wide-EP disaggregated prefill this is fatal: 0-token EP peers still launch `deep_gemm.fp8_fp4_mega_moe` every layer and wait for the compiling rank inside the kernel's NVLink barrier, which device-traps after 180 s. The 23-bucket burst (one DeepGEMM `tf32_hc_prenorm_gemm` + one TileLang big-fuse variant per bucket) measures **159–166 s on a cold JIT cache on GB200**, so any >~15 s trigger stagger between ranks blows the budget:

```
DeepGEMM NVLink barrier timeout (180s): rank=2, counter=550, signal=7, target=8, phase=1, sign=0, tag=1
Assertion failed: .../deep_gemm/include/deep_gemm/comm/barrier.cuh:76
→ tvm.error.InternalError: CUDA driver error (sm100_fp8_fp4_mega_moe.hpp): 719 (CUDA_ERROR_LAUNCH_FAILED)
```

Reproduces deterministically on GB200 disagg 1p1d dep8-dep16 (8k1k); currently worked around by `SGLANG_DSV4_MHC_PREWARM=0`. Single-node dep4 setups pass only because their triggers happen to align (skew ≪ 180 s) — verified by a synthetic 4-rank repro where a single 200 s host stall reproduces the exact barrier-timeout signature.

## Modifications

- Trigger the same prewarm from the tail of `DeepseekV4ForCausalLM.load_weights` on every rank — before the memory pool, CUDA-graph capture, and any forward — then `get_tp_group().barrier()` so no rank proceeds while a peer is still compiling, and `torch.cuda.empty_cache()` (this now runs before `init_memory_pool`, so the multi-GB transient prewarm buffers must not skew KV-pool sizing).
- Keep the in-forward trigger as a fallback for entry points that bypass `load_weights` (e.g. kernel unit tests); add prewarm duration + rank-sync logs.
- Remove the orphaned `prewarm_mhc_token_counts/_buckets` pair (added by #25810, removed by #26238, resurrected without a caller by the #25976 merge).

## Accuracy Tests

No kernel/model math changes — the prewarm replays the existing `_mhc_pre_impl` path with dummy inputs at load time (same code the lazy trigger ran). Server responses validated on DSV4-Flash (TP4+DP4+deepep) and DSV4-Pro (disagg dep8/dep16).

## Speed Tests and Profiling

A/B on GB200 disagg 2-node dep8 prefill + 4-node dep16 decode — same recipe, container, and base commit; the only difference is this patch:

| | without fix | with fix |
|---|---|---|
| prewarm trigger | 1 rank, mid-serving | all 8 prefill ranks at load (153–173 s, rank sync +0.0 s) |
| NVLink barrier timeouts | 16 (fields match production crash) | **0** |
| sa-bench (isl 8192 / osl 1024, conc 8) | crash, no results | completes, 80/80 requests, 464 tok/s output |

Startup cost is unchanged (~160 s one-shot on a cold JIT cache; ~0 s warm — same as the lazy trigger paid, just moved off the serving path and aligned across ranks).

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28634631368](https://github.com/sgl-project/sglang/actions/runs/28634631368)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28634631251](https://github.com/sgl-project/sglang/actions/runs/28634631251)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
