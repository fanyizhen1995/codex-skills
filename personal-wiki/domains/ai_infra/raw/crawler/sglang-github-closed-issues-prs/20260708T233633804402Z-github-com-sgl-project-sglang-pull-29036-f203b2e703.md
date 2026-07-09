---
source_id: sglang-github-closed-issues-prs
title: '[Bugfix] Fix DeepSeek-V4 FP8 wo_a scale layout for DeepGEMM'
canonical_url: https://github.com/sgl-project/sglang/pull/29036
captured_at: '2026-07-08T23:36:33.804402+00:00'
content_hash: f203b2e7037490a5388490f828742c5127b7083120d08334cecac91c8163531d
---
# [Bugfix] Fix DeepSeek-V4 FP8 wo_a scale layout for DeepGEMM

URL: https://github.com/sgl-project/sglang/pull/29036
State: closed
Labels: high priority, deepseek
Closed at: 2026-07-08T00:42:26Z
Merged at: 

## Summary

Fix the DeepSeek-V4 FP8 `wo_a` DeepGEMM path by quantizing the activation in group-major `[G, T, D]` order and preserving the TMA-aligned packed UE8M0 scale layout consumed by DeepGEMM on SM100.

## Problem

The existing path quantizes `o: [T, G, D]` as a flat `[T * G, D]` tensor and then views the scales back as `[T, G, -1]`. For the SM100 DeepGEMM FP8 einsum path, the activation scale buffer needs group-major, TMA-aligned layout semantics. Flattening across `T * G` can associate scales with the wrong group.

## Fix

- Add a private DeepSeek-V4 `wo_a` helper that accepts `[G, T, D]` activation input.
- Write each group's `[T, D]` activation quantization into a preallocated TMA-aligned packed UE8M0 scale buffer.
- Pass the logical `[T, G, ...]` activation/scale views to `deep_gemm.fp8_einsum` without making the scale tensor contiguous.

This only changes the existing `SGLANG_OPT_FP8_WO_A_GEMM` path. No new runtime flag is added.

## Tests

The GPU tests below were run locally on a Blackwell GPU.

```text
PYTHONPATH=python python -m pytest test/registered/jit/test_deepseek_v4_fp8_wo_a.py -q -s
# 1 passed

PYTHONPATH=python python -m pytest test/registered/quant/test_fp8_kernel.py -q -s
# 2 passed

PYTHONPATH=python python -m pytest test/registered/quant/test_fused_rms_fp8_group_quant.py -q -s
# 1 skipped in this environment

python -m py_compile python/sglang/srt/models/deepseek_v4.py test/registered/jit/test_deepseek_v4_fp8_wo_a.py
python -m isort --check-only python/sglang/srt/models/deepseek_v4.py test/registered/jit/test_deepseek_v4_fp8_wo_a.py
python -m black --check python/sglang/srt/models/deepseek_v4.py test/registered/jit/test_deepseek_v4_fp8_wo_a.py
git diff --check
```

I also verified the new regression test fails against current `origin/main` when importing the old DeepSeek-V4 implementation, while it passes on this branch.

## Risk

Low. The change is scoped to the DeepSeek-V4 FP8 `wo_a` DeepGEMM path on SM100+.





















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28024903795](https://github.com/sgl-project/sglang/actions/runs/28024903795)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28542390805](https://github.com/sgl-project/sglang/actions/runs/28542390805)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
