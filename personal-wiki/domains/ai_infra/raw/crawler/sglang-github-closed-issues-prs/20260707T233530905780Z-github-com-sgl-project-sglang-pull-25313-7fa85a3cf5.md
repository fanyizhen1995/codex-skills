---
source_id: sglang-github-closed-issues-prs
title: amd/deepseek_v4 integration 23/N new compressor decode fix
canonical_url: https://github.com/sgl-project/sglang/pull/25313
captured_at: '2026-07-07T23:35:30.905780+00:00'
content_hash: 7fa85a3cf55417f79dcc1c9439110e93b69baff8cc1d53c0334d7907dc4b52eb
---
# amd/deepseek_v4 integration 23/N new compressor decode fix

URL: https://github.com/sgl-project/sglang/pull/25313
State: closed
Labels: deepseek
Closed at: 2026-05-15T15:46:54Z
Merged at: 

Update amd/deepseek_v4 integration branch

Following PRs have large set of conflict, we use this PR and upstream amd/deepseek_v4 branch to integrate in parallel.
https://github.com/sgl-project/sglang/pull/23600
https://github.com/sgl-project/sglang/pull/23608

## Motivation

22/N (#25164) enabled `SGLANG_OPT_DPSK_V4_RADIX=1` on ROCm and noted a +56% TPOT regression in decode-heavy workloads as a known follow-up. To isolate the root causes we ran three configurations on DSv4-Pro-FP8, 8x MI35X TP=8 (random, in=512, out=2048):

| Config | `OLD_COMPRESSOR` | `RADIX` | Mean TPOT (c=2) | vs baseline |
|--------|------------------|---------|----------------|-------------|
| 1 — Baseline | `true` | 0 | 21.06 ms | — |
| 2 — New compressor, no radix | `false` | 0 | 28.69 ms | +35% |
| 3 — Full radix | `false` | 1 | 34.23 ms | +56% |

Config 2 vs 1 isolates the compressor switch (+35%); config 3 vs 2 isolates the paged radix path (+21%). This PR addresses the 35% compressor regression via two bug fixes.

**Bug 1 — unguarded `flash_mla` import in `deepseek_v4_backend_radix.py`:**
`_create_flashmla_metadata` unconditionally imports `flash_mla`, which is unavailable on ROCm, crashing at decode initialization when the radix backend is active. Fixed by routing through the HIP-aware factory in `compressed/metadata.py`.

**Bug 2 — new compressor decode path missing fused Triton kernels:**
`compress_decode` (`OLD_COMPRESSOR=false`, `RADIX=0`) runs pool write + overlap shift + APE add + softmax + weighted sum as 6 unfused PyTorch launches. The existing `fused_compress_c4_decode_old_triton` / `fused_compress_c128_decode_chunked_kernel` in `fused_compress_old_triton.py` already collapse all of this into a single 2D-grid Triton launch but were only wired into `compress_decode_old`. Since the `DeepSeekV4CompressState` tensor layout is identical between OLD and NEW paths, adding the same `use_hip_fused_compress` + ratio/overlap guard to `compress_decode` neutralizes the +35% regression.

## Modifications

- `python/sglang/srt/layers/attention/deepseek_v4_backend_radix.py`: route `_create_flashmla_metadata` through HIP-aware factory from `compressed/metadata.py` to prevent import crash on ROCm.
- `python/sglang/srt/models/deepseek_v4.py`: add `use_hip_fused_compress` guard in `compress_decode` to call `fused_compress_c4_decode_old_triton` / `fused_compress_c128_decode_chunked_kernel` when ratio/overlap match; existing PyTorch path becomes the `else` fallback.

## Accuracy Tests

few-shot GSM8K (8-shot, 200 questions) on DSv4-Pro-FP8, 8x MI35X TP=8, `OLD_COMPRESSOR=false` `RADIX=0`:

| accuracy | invalid | CI threshold |
|----------|---------|--------------|
| 0.940 | 0.005 | >0.91 — pass |

## Speed Tests and Profiling

Decode-heavy workload (random, in=512, out=2048) on DSv4-Pro-FP8, 8x MI35X TP=8: the two fixes neutralize the +35% TPOT regression from the compressor switch, restoring full parity with the `OLD_COMPRESSOR=true` baseline.

## Future Work

The remaining 21% TPOT gap with `RADIX=1` is a follow-up.

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.

- Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`

1. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.
