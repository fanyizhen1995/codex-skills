---
source_id: sglang-github-closed-issues-prs
title: 'cookbook(deepseek-v4): add MORI disagg backend for AMD + bump MI355X image'
canonical_url: https://github.com/sgl-project/sglang/pull/30651
captured_at: '2026-07-15T23:40:28.372732+00:00'
content_hash: 35bc2b77cc4451286404538a2b2acd9120840f361f0ac336c4dece83c4e4a345
---
# cookbook(deepseek-v4): add MORI disagg backend for AMD + bump MI355X image

URL: https://github.com/sgl-project/sglang/pull/30651
State: closed
Labels: documentation, deepseek
Closed at: 2026-07-15T07:33:06Z
Merged at: 2026-07-15T07:33:06Z

## Summary

- Add **MORI** as a PD-disaggregation transfer backend option in the DeepSeek-V4 Playground, gated to MI300X/MI355X hardware via `requiresHw`.
- Bump MI355X docker image to `v0.5.14-rocm720-mi35x-20260708`.
- Update all MI355X cells with latest InferenceX benchmark tuning (PRs #2093, #2108).

## Changes

### MORI Disagg Backend (from InferenceX #1818)
- Added MORI transfer backend to `pdDisagg.transferBackends`, gated to `mi300x`/`mi355x`.

### MI355X Cell Updates (from InferenceX #2093 / #2108)

**perf-changelog (InferenceX #2093 — DSV4 non-MTP):**
- Bump image to `lmsysorg/sglang-rocm:v0.5.14-rocm720-mi35x-20260706`
- Clean the export envs
- Enable two batch overlap

**perf-changelog (InferenceX #2108 — DSV4 MTP):**
- Bump image to `lmsysorg/sglang-rocm:v0.5.14-rocm720-mi35x-20260708`
- Clean the export envs

**Specific changes applied to cookbook cells:**
- Docker image: `v0.5.14-rocm720-mi35x-20260708` (latest from #2108)
- `--swa-full-tokens-ratio`: 0.1 → 0.15 (all 12 MI355X cells)
- New DP-attention env vars (8 balanced/high-throughput cells):
  - `SGLANG_SHARED_EXPERT_TP1=1`
  - `SGLANG_DP_SHARED_EXPERT_LOCAL=1`
  - `SGLANG_DP_USE_REDUCE_SCATTER=1`
- Replace `--enable-prefill-delayer` + `--prefill-delayer-max-delay-ms 5000` with `--enable-two-batch-overlap` (8 DP-attention cells)

## References

- SemiAnalysisAI/InferenceX#1818 (MORI disagg)
- SemiAnalysisAI/InferenceX#2093 (DSV4 non-MTP updates)
- SemiAnalysisAI/InferenceX#2108 (DSV4 MTP updates)

cc @zijiexia















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29397391635](https://github.com/sgl-project/sglang/actions/runs/29397391635)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29397391425](https://github.com/sgl-project/sglang/actions/runs/29397391425)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
