---
source_id: sglang-github-closed-issues-prs
title: '[AMD] add dedicated jit-kernel-benchmark-test-amd stage + register portable
  JIT benches'
canonical_url: https://github.com/sgl-project/sglang/pull/30307
captured_at: '2026-07-09T23:36:35.342479+00:00'
content_hash: d69f5b6ac0f88a9028037f2ef53de50b39a24dc4aab7660ce314c04b308220a3
---
# [AMD] add dedicated jit-kernel-benchmark-test-amd stage + register portable JIT benches

URL: https://github.com/sgl-project/sglang/pull/30307
State: closed
Labels: quant, amd, hicache, run-ci
Closed at: 2026-07-09T01:09:05Z
Merged at: 2026-07-09T01:09:05Z

## Summary
Gives AMD a **dedicated JIT kernel benchmark stage** (`jit-kernel-benchmark-test-amd`), mirroring NVIDIA's split between `base-b-kernel-unit-test-*` and `base-b-kernel-benchmark-test-*` (rather than folding benches into the `jit-kernel-unit-test-amd` unit-test job), and registers the ROCm-passing kernel benchmarks to it.

- **Registrations** use `stage="jit-kernel-benchmark", runner_config="amd"` (effective suite `jit-kernel-benchmark-test-amd`), matching the NV `stage="base-b-kernel-benchmark"` convention.
- **`test/run_suite.py`**: registers the `jit-kernel-benchmark-test-amd` suite.
- **`pr-test-amd.yml` + `pr-test-amd-rocm720.yml`**: add a sibling `jit-kernel-benchmark-test-amd` job (dispatch dropdown option, `jit_kernel` change-detection gating, finish/aggregation `needs`) running `run_suite.py --hw amd --suite jit-kernel-benchmark-test-amd`.
- NVIDIA-hardware-specific benches (nvfp4 / mxfp8 / sm90 / dsv4-fp4-indexer) are intentionally left CUDA-only.

## Scope: ROCm-passing subset (16 benches)
An initial dispatch of all 35 candidate benches showed 16/35 pass on MI325; the 19 failing ones (CUDA-only kernel source, missing ROCm `sgl_kernel` ops, or missing libs like `flashinfer`/`deep_gemm`) were dropped back to CUDA-only and are follow-up ROCm porting work. This PR registers only the **16 passing** benches.

## Verification
The `jit-kernel-benchmark-test-amd` stage is green on **both ROCm targets** — Test Summary **16/16 passed** on each:

- **ROCm 7.2** (`pr-test-amd-rocm720.yml`, MI325, `continue_on_error=false`) → [Run #28845957451](https://github.com/sgl-project/sglang/actions/runs/28845957451)
- **ROCm 7.0** (`pr-test-amd.yml`, default image, MI325) → [Run #28894117319](https://github.com/sgl-project/sglang/actions/runs/28894117319)

Per-bench runtime on ROCm (MI325), from that run:

| # | Bench | elapsed (s) |
| - | ----- | ----------: |
| 1 | `bench_activation.py` | 14 |
| 2 | `bench_add_constant.py` | 7 |
| 3 | `bench_clamp_position.py` | 11 |
| 4 | `bench_dsv3_router_gemm.py` | 4 |
| 5 | `bench_fused_eh_norm.py` | 7 |
| 6 | `bench_hicache.py` | 11 |
| 7 | `bench_hisparse.py` | 34 |
| 8 | `bench_mla_kv_pack_quantize_fp8.py` | 7 |
| 9 | `bench_ngram_compute_decode.py` | 4 |
| 10 | `bench_ngram_update_token_table.py` | 7 |
| 11 | `bench_online_c128_mtp.py` | 12 |
| 12 | `bench_resolve_future_token_ids.py` | 11 |
| 13 | `bench_store_cache.py` | 21 |
| 14 | `diffusion/bench_qwen_image_modulation.py` | 14 |
| 15 | `minimax/bench_minimax_decode_topk.py` | 15 |
| 16 | `minimax/bench_minimax_store_kv_index.py` | 6 |
| | **Total** | **~185** |

Other checks: AST parser confirms the 16 benches resolve to effective suite `jit-kernel-benchmark-test-amd` (the 4 kv_canary nightly benches correctly stay on `nightly-amd-kernel-1-gpu`); both workflow YAMLs validate; `run_suite.py` compiles and lists the new suite.

## Test plan
- [x] Run `jit-kernel-benchmark-test-amd` on ROCm and confirm the registered subset passes ([16/16 green](https://github.com/sgl-project/sglang/actions/runs/28845957451)).
- [ ] Follow-up: port/guard the 19 CUDA-only benches and add them incrementally.









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28966860749](https://github.com/sgl-project/sglang/actions/runs/28966860749)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28966860605](https://github.com/sgl-project/sglang/actions/runs/28966860605)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
