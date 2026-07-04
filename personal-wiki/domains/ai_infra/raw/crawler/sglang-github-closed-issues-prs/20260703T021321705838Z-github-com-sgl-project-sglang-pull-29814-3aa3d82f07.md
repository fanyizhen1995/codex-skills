---
source_id: sglang-github-closed-issues-prs
title: '[AMD] ci: register page-major Qwen3.5-4B GDN-hybrid test on extra-a 1-gpu-large-amd'
canonical_url: https://github.com/sgl-project/sglang/pull/29814
captured_at: '2026-07-03T02:13:21.705838+00:00'
content_hash: 3aa3d82f07a78dd1b7d74534cdae210a3575a9607889967ede34d45b28a6cd10
---
# [AMD] ci: register page-major Qwen3.5-4B GDN-hybrid test on extra-a 1-gpu-large-amd

URL: https://github.com/sgl-project/sglang/pull/29814
State: closed
Labels: 
Closed at: 2026-07-02T04:02:33Z
Merged at: 

## Summary

Registers `test/registered/page_major/test_page_major_qwen_hybrid.py` for AMD (`extra-a-test-1-gpu-large-amd`).

It launches Qwen3.5-4B (a GDN / linear-attention / mamba hybrid) with `--enable-page-major-kv-layout` on **all-triton** backends (`--attention-backend triton --linear-attn-backend triton --mamba-backend triton`) and asserts GSM8K accuracy ≥ 0.80 (baseline ~0.86, so real margin). No FlashInfer/FA3/FA4, no mxfp4, no quant kernels.

Why this is ROCm-viable: the GDN / linear-attn triton kernels are already AMD-proven per-commit (`attention/unittests/gdn/test_triton.py` runs on `stage-b-*-amd`), and the gate is a forgiving accuracy check. Picked from an extra-tier gap audit as the one cleanly-addable candidate (its `page_major/test_page_major_gpt_oss.py` sibling stays CUDA-only — gpt-oss mxfp4).

Verifying on both AMD lanes; drop the `register_amd_ci` line if it trips (no register-and-skip). `register_cuda_ci` unchanged.

## Test plan

Verifying on both AMD extra lanes (dispatched via `pr-test-amd-extra.yml`, branch rebased onto current `main`; baseline on `main` is green for both `1-gpu-large-amd` and `1-gpu-small-amd`, so these results are attributable):

- [ ] `extra-a-test-1-gpu-large-amd` (mi325) green — [run 28554775031](https://github.com/sgl-project/sglang/actions/runs/28554775031)
- [ ] `extra-a-test-1-gpu-large-amd-rocm720` green — [run 28554781526](https://github.com/sgl-project/sglang/actions/runs/28554781526)

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28554777621](https://github.com/sgl-project/sglang/actions/runs/28554777621)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28554777554](https://github.com/sgl-project/sglang/actions/runs/28554777554)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
