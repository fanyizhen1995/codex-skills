---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Gate broken CK block-FP8 GEMM shapes to aiter-triton-GEMM to fix ROCm
  7.0 Qwen3.5 accuracy'
canonical_url: https://github.com/sgl-project/sglang/pull/29918
captured_at: '2026-07-03T02:13:21.692682+00:00'
content_hash: c2db31c39fce3ea03fbc3ce33afb4b4050b53688c31eedf5eaca54169a5c632a
---
# [AMD] Gate broken CK block-FP8 GEMM shapes to aiter-triton-GEMM to fix ROCm 7.0 Qwen3.5 accuracy

URL: https://github.com/sgl-project/sglang/pull/29918
State: closed
Labels: run-ci
Closed at: 2026-07-03T01:18:37Z
Merged at: 2026-07-03T01:18:37Z


## Motivation
The Qwen3.5-397B-A17B-FP8 accuracy test fails on **AMD gfx950 (MI35x) with ROCm 7.0**: GSM8K drops to ~0.24 with a ~67% invalid-output rate. The same code/model/args pass on ROCm 7.2 (~0.95).
### Root cause
On gfx95, the bpreshuffle CK block-scale FP8 GEMM is disabled for ROCm < 7.2 because ROCm 7.0 hipcc miscompiles it (PR23319). The dense FP8 linear path then falls back to the non-bpreshuffle `ck_gemm_a8w8_blockscale`, which **returns NaN above a per-shape M threshold** on ROCm 7.0 gfx95:

| Shape (n, k) | CK correct up to | NaN at | ROCm 7.2 CK |
| --- | --- | --- | --- |
| (2560, 4096) | M = 2048 | M ≥ 4096 | correct |
| (4096, 1024) | M = 4096 | M ≥ 8192 | correct |

These are Qwen3.5's dense FP8 attention projections. Prefill (chunked up to 16384 tokens) exceeds the threshold, so the NaN corrupts prefilled sequences → garbage/invalid outputs. A minimal unit test (same fp8 inputs → CK vs Triton vs fp32 ref) confirms CK returns NaN on ROCm 7.0 while Triton matches the fp32 reference for all M; on ROCm 7.2 the same CK call is correct for all M (incl. 16384).
## Modifications
Only on the affected environment (gfx95 + ROCm < 7.2), fall back to the numerically-correct Triton FP8 block GEMM **for the affected shapes above their measured CK-safe M**, keeping the (faster) CK path for small M (e.g. decode) and leaving every other shape and ROCm ≥ 7.2 / non-gfx95 untouched.
- Add `_AITER_GFX95_CK_W8A8_MAX_SAFE_M = {(2560, 4096): 2048, (4096, 1024): 4096}` (conservative = last verified-safe M).
- In `aiter_w8a8_block_fp8_linear`, the `_use_aiter_gfx95` (ROCm < 7.2) branch now also selects Triton when `M > _AITER_GFX95_CK_W8A8_MAX_SAFE_M[(n, k)]`.
## Accuracy Results
Qwen3.5-397B-A17B-FP8, tp=8, dcp=2, `--attention-backend triton`, GSM8K (1319):
| Config | ROCm | Accuracy | Invalid |
| --- | --- | --- | --- |
| Before (CK) | 7.0 | 0.244 | 0.666 |
| **After (this PR)** | **7.0** | **0.950** | ~0.01 |
| Reference | 7.2 | 0.945 | 0.009 |


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
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.





















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28579547755](https://github.com/sgl-project/sglang/actions/runs/28579547755)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28579547352](https://github.com/sgl-project/sglang/actions/runs/28579547352)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
