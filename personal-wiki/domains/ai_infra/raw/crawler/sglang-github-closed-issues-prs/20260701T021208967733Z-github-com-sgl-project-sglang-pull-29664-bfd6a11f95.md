---
source_id: sglang-github-closed-issues-prs
title: '[Diffusion] Reuse shared AlignedVector and tidy jit_kernel/diffusion'
canonical_url: https://github.com/sgl-project/sglang/pull/29664
captured_at: '2026-07-01T02:12:08.967733+00:00'
content_hash: bfd6a11f9508717e2093f9eba0cfa0db48683c42a7735925ca771efb82a7d9c6
---
# [Diffusion] Reuse shared AlignedVector and tidy jit_kernel/diffusion

URL: https://github.com/sgl-project/sglang/pull/29664
State: closed
Labels: run-ci, jit-kernel
Closed at: 2026-06-30T03:38:23Z
Merged at: 2026-06-30T03:38:23Z

## Motivation

The KDA-Pilot diffusion native-CUDA fast paths each need a 128-bit vectorized load/store. The first one that landed (`norm_scale_shift`, #27392) already uses the shared `device::AlignedVector` component from `sgl_kernel/vec.cuh`, but the two newer kernels (#29281, #29361) still hand-roll their own local `union`. This PR makes all the diffusion CUDA kernels reuse the shared `AlignedVector` component instead of a per-kernel `union`, and folds in a few small, verified cleanups found while reviewing the rest of `jit_kernel/diffusion/`. No behavior change.

## Modifications

**Native CUDA (`.cuh`) — reuse `device::AlignedVector`:**
- `residual_gate_add`: replace `union Vec16<T>` with `device::AlignedVector<T, kVec>` (`.load()`/`.store()`/`operator[]`).
- `causal_conv3d_cat_pad`: replace `union Pack` with `device::AlignedVector<ET, kVec>` (scattered scalar reads stay scalar `__ldg`; only the vectorized store changes).
- `timestep_embedding`: replace raw `float4` with `AlignedVector<float, 4>`, and add `#pragma once` + a named namespace `sglang_timestep_embedding` to match its siblings (plus the matching wrapper symbol in `timestep_embedding.py`).

**CuTe-DSL / Triton cleanups:**
- Hoist the byte-identical `to_cute_arg` / `to_fake_cute_args` helpers into `cutedsl/utils.py` and import them in both kernel files (removes ~36 duplicated lines).
- Fix a copy-paste guard in `norm_tanh_mul_add_norm_scale` (`isinstance(src, …) and isinstance(src, …)` → `… isinstance(dst, …)`, matching the sibling).
- Delete the dead `_precompute_inv_rms` in `sana_wm_gdn` (superseded by `fused_qk_inv_rms`; no callers).
- Drop the unused `rows` parameter from the `scale_shift` 4D kernel and its call site.
- Drop unused `B, S` args from `validate_weight_bias` (only `D` is used; matches the sibling signature).
- Remove stale commented-out code (`norm.py`, `scale_residual_norm_scale_shift.py`) and fix a stale docstring module name in `sana_wm_gdn`.

## Accuracy Tests

Validated on B200 (`pytest`, all pass):
- `test/registered/jit/diffusion/{test_residual_gate_add, test_causal_conv3d_cat_pad, test_fused_norm_scale_shift, test_qwen_image_modulation}.py`
- `test/registered/jit/test_timestep_embedding.py`

A torch-reference smoke over every touched kernel (the 4 CuTe-DSL modulation entries, the 4D `scale_shift` path, `sana_wm_gdn.fused_qk_inv_rms`, plus a negative test that `validate_weight_bias` still rejects bad shapes) matches within bf16 tolerance.

## Speed Tests and Profiling

Before/after on **B200**, OLD = `union`/`float4`, NEW = `AlignedVector` (`cuda` column from the registered benches; medians).

**`bench_residual_gate_add` — `cuda` µs (neutral):**

| workload | OLD | NEW |
|---|---:|---:|
| ltx2_bcast_s32640_c4096 | 126.35 | 125.97 |
| ltx2_full_s8160_c4096 | 41.64 | 41.65 |
| ideogram4_bcast_s4096_c4608 | 23.23 | 23.27 |
| flux2_bcast_s4608_c3072 | 16.02 | 16.05 |
| flux2_bcast_s512_c3072 | 15.93 | 15.68 |
| ltx2_full_s126_c2048 | 13.98 | 13.94 |

**`bench_causal_conv3d_cat_pad` — `cuda` µs (within noise):**

| case | OLD | NEW |
|---|---:|---:|
| c512_t4_h120_w208_cache1 | 126.98 | 129.02 |
| c512_t4_h120_w208_cache2 | 151.55 | 151.61 |
| c256_t4_h240_w416_cache1 | 230.4 | 232.4 |
| c256_t4_h240_w416_cache2 | 274.40 | 276.48 |

The conv3d numbers wobble <1%. To rule out a real regression I diffed the generated SASS of the bf16 `cat_pad_flat_kernel` (largest shape) for OLD vs NEW:

- **identical instruction count: 1184 vs 1184**
- **1× `STG` (a single 128-bit store) and 8× `LDG`** in both — i.e. `AlignedVector::store` lowers to the same `STG.128` as the old `uint4` union
- **0 local-memory ops (`STL`/`LDL` = 0)** in both — no register spilling
- only difference: a single `IMAD`↔`IADD3` scheduling swap (467/127 vs 468/126)

`ncu` agrees: same DRAM throughput (~18.5%), same SM throughput (~81%), zero local load/store sectors in both. The kernel is SM-issue-bound, so the sub-1% wall-clock difference is compiler-scheduling/measurement noise, not an algorithmic or memory regression.

`timestep_embedding` has no registered bench; it is a tiny vectorized store kernel covered by `test_timestep_embedding.py` (the `float4` → `AlignedVector<float,4>` change keeps a single 128-bit store).

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests). (No new tests — behavior-preserving cleanup covered by existing diffusion unit tests.)
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results.
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

🤖 Generated with [Claude Code](https://claude.com/claude-code)



<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28380606742](https://github.com/sgl-project/sglang/actions/runs/28380606742)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28380606530](https://github.com/sgl-project/sglang/actions/runs/28380606530)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
