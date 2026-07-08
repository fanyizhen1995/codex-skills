---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Fix DeepSeek-V4 fp8 KV path on gfx942 (e4m3fnuz)'
canonical_url: https://github.com/sgl-project/sglang/pull/28455
captured_at: '2026-07-07T23:35:30.905275+00:00'
content_hash: c4e78127c0e87aa34ffe3e34727da07ab8ba49b4f010ebb08bb9987e7238add1
---
# [AMD] Fix DeepSeek-V4 fp8 KV path on gfx942 (e4m3fnuz)

URL: https://github.com/sgl-project/sglang/pull/28455
State: closed
Labels: amd, deepseek, run-ci, jit-kernel
Closed at: 2026-06-24T00:45:14Z
Merged at: 2026-06-24T00:45:14Z

## Motivation
The DeepSeek-V4 `triton` flashmla fp8 path assumed CUDA / gfx950 (CDNA4) `e4m3fn`, but
gfx942 (MI300 / MI325, CDNA3) uses `e4m3fnuz`. The two formats differ in exponent bias,
max value, and bit patterns, so on gfx942 the fp8 KV path collapses GSM8K accuracy
(~0.00) and emits NaNs in the sampler.

These changes arch-gate the fp8 store / decode / quant paths for `fnuz` so the default
`triton` flashmla backend is correct on gfx942. gfx950 behavior is unchanged.

## Modifications

- **fp8 fnuz underflow → NaN** — `jit_kernel/include/sgl_kernel/deepseek_v4/fp8_utils.cuh`
  (`cvt_float_to_fp8_e4m3`): on `e4m3fnuz`, byte `0x80` is NaN (not `-0.0`). An
  underflowing negative returned `0x80`, poisoning the compressed KV cache. Flush
  underflow to `+0` under fnuz.
- **fp8 store / decode dtype match** — arch-gate the flashmla KV store to `float8e4b8`
  (fnuz / gfx942) vs `float8e4nv` (fn / gfx950) to match the decode bitcast; gate the
  decode KV dequant to `e4m3fnuz` on gfx942.
  (`fused_qk_norm_rope_store.py`, `nsa/triton_decode/triton_mla_kernels_decode_fused.py`)
- **arch-aware fp8 max** — `kFP8E4M3Max` (224 fnuz / 448 fn) for fp8 quant scale/clamp
  across the compute path; the compressed-KV and indexer / index-K fp8 stores use the
  arch-aware clip max for the UE8M0 scale divisor, fixing gfx942 under-scaling.
  (`math.cuh`, `fused_norm_rope_v2.cuh`, `store.cuh`, `dsa/fused_store_index_cache.cuh`)

  For reference, the platform-dependent `kFP8E4M3Max` is defined in
  `python/sglang/jit_kernel/include/sgl_kernel/type.cuh`:

  ```cpp
  // ---------------------------------------------------------------------------
  // FP8 max clamp value — platform-dependent
  //   CUDA (e4m3fn):       448.0f
  //   AMD FNUZ (e4m3fnuz): 224.0f
  //   AMD E4M3 (e4m3fn):   448.0f
  // ---------------------------------------------------------------------------
  #ifndef USE_ROCM
  constexpr float kFP8E4M3Max = 448.0f;
  #else  // USE_ROCM
  #if HIP_FP8_TYPE_FNUZ
  constexpr float kFP8E4M3Max = 224.0f;
  #else   // HIP_FP8_TYPE_E4M3
  constexpr float kFP8E4M3Max = 448.0f;
  #endif  // HIP_FP8_TYPE_FNUZ
  #endif  // USE_ROCM
  ```
- **zero-init `q_padded`** — `models/deepseek_v4.py`: uninitialized TP padding heads could
  inject NaN into attention; allocate with `new_zeros`.

## Accuracy Tests

GSM8K 5-shot, full 1319 questions, tp8, gfx942 (MI325), `triton` flashmla fp8:

| | accuracy | invalid |
|---|---|---|
| before | ~0.00 | — |
| after | 0.911 | 0.000 |

No NaN-in-sampler warnings after the fix.


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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #27709798445](https://github.com/sgl-project/sglang/actions/runs/27709798445)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #27750989075](https://github.com/sgl-project/sglang/actions/runs/27750989075)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
