---
source_id: sglang-github-closed-issues-prs
title: '[AMD] [GLM5] GLM-5.1 MXFP4 (MI355X) + enable EAGLE for gfx950 in cookbook'
canonical_url: https://github.com/sgl-project/sglang/pull/29194
captured_at: '2026-07-07T23:35:30.906303+00:00'
content_hash: eeadc676db110e623c035ab1fefd9db358e5209921b60c911506f36fda46e068
---
# [AMD] [GLM5] GLM-5.1 MXFP4 (MI355X) + enable EAGLE for gfx950 in cookbook

URL: https://github.com/sgl-project/sglang/pull/29194
State: closed
Labels: documentation, amd
Closed at: 2026-06-25T10:54:48Z
Merged at: 2026-06-25T10:54:48Z

## Motivation

The [SGLang Cookbook](https://docs.sglang.io/cookbook) GLM-5.1 page documents AMD deployment only for the BF16/FP8 checkpoints, does not cover the MXFP4 checkpoint (`amd/GLM-5.1-MXFP4`) on MI355X (gfx950), and states that EAGLE speculative decoding is unsupported on AMD (with the deploy generator gating it off for all AMD GPUs). This follows up #28975 (opt-in Triton fp8 sparse-MLA prefill kernel for gfx950) and corrects the EAGLE support status for gfx950.

## Modifications

- **`glm-51-deployment.jsx`** (interactive deploy generator):
  - Add an `MXFP4` quantization option, enabled and default on MI355X (gfx950); disabled on other hardware. Add `mi355x.mxfp4 = { tp: 4, mem: 0.85 }`; generate `--model-path amd/GLM-5.1-MXFP4 --tp 4 --kv-cache-dtype fp8_e4m3` plus the existing AMD tilelang / chunked-prefill / watchdog flags.
  - **EAGLE emit change:** the old generator gated the Speculative Decoding toggle off for all AMD, and the old cookbook said EAGLE was unsupported on AMD. We later tested EAGLE on gfx950 (MI355X) and it works; gfx942 (MI300X/MI325X) is unverified. The generator now emits the EAGLE flags by default and excludes them **only on MI300X/MI325X (gfx942)**. The (useless on/off) Speculative Decoding toggle was removed in favor of always emitting the flags where supported.
- **`GLM-5.1.mdx`**:
  - Add an `MXFP4` column to the hardware table (tp=4 on MI355X). Add a `MXFP4 (MI355X / gfx950)` command block in section 4.2 (prefixed with the optional `SGLANG_DSA_TRITON_PREFILL=1`, and including the EAGLE flags).
  - AMD note: "EAGLE speculative decoding is supported on MI355X (gfx950) and unverified on MI300X/MI325X (gfx942)" (was: "not currently supported on AMD").

## Verification

Built locally with `mint dev` / `mint validate` (build validation passed). EAGLE on MI355X validated separately on hardware (lossless GSM8K, large ITL/throughput improvement). gfx942 (MI300X/MI325X) EAGLE verification can be a follow-up.

Scope: GLM-5.1 only; MXFP4 + EAGLE on MI355X (gfx950).







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28133913757](https://github.com/sgl-project/sglang/actions/runs/28133913757)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28151181987](https://github.com/sgl-project/sglang/actions/runs/28151181987)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
