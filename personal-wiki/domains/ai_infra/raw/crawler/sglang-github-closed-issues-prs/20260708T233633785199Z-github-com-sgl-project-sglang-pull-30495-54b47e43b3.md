---
source_id: sglang-github-closed-issues-prs
title: 'ci(nightly): add force_baseline_update dispatch input for precision job'
canonical_url: https://github.com/sgl-project/sglang/pull/30495
captured_at: '2026-07-08T23:36:33.785199+00:00'
content_hash: 54b47e43b38b09dd7948a4a2713f27f1bc4f95712087645800cd57679dc1f514
---
# ci(nightly): add force_baseline_update dispatch input for precision job

URL: https://github.com/sgl-project/sglang/pull/30495
State: closed
Labels: run-ci
Closed at: 2026-07-08T23:27:42Z
Merged at: 2026-07-08T23:27:42Z

## Problem

`nightly-test-precision-8-gpu-h200` has been red every night since 2026-07-07:

- 07-07 run 28833675242: `non_intrusive__model.layers.16.inputs.1  rel_diff=0.009655330045  vs threshold 1e-3`
- 07-08 run 28909052814: identical tensor, `rel_diff=0.009655330366` — deterministic drift against a frozen baseline.

Only model: `zai-org/GLM-5.2-FP8` (the suite's default, TP=8).

## Root cause — PR #29783 (intentional, not a regression)

#29783 ("Fixes for NVFP4 numerical accuracy for router GEMM output and wrong correction bias cast", merged 2026-07-06 20:53 UTC, merge commit `d8462f4961`) changed `DeepseekV2MoEGate.forward` in `python/sglang/srt/models/deepseek_v2.py`. On the non-dsv4 CUDA branch, the router GEMM moved from `F.linear(hidden_states, self.weight)` (bf16 output) to `linear_bf16_fp32(hidden_states, self.weight)` (fp32 output) — a cuBLAS `bf16 x bf16 -> fp32` GEMM:

```diff
-                logits = F.linear(hidden_states, self.weight, None)
+                # cuBLAS bf16 x bf16 -> fp32 GEMM (torch.mm's out_dtype kwarg is CUDA-only)
+                from sglang.jit_kernel.dsv4 import linear_bf16_fp32
+                logits = linear_bf16_fp32(hidden_states, self.weight)
```

GLM-5.2 uses the noaux_tc gate, which takes exactly this branch, so the router-logits precision shift produces a ~1% accumulated residual-stream drift by layer 16. This is an expected, one-time numerical step from a correct accuracy fix — **not a regression**. The nightly baseline, however, was frozen pre-#29783, so every comparison since has blown past the 1e-3 threshold.

## Why it can't self-heal

The baseline store (`python/sglang/test/precision_baseline_store.py::_select_latest_run`) deliberately skips rows with `pass_label="failed"` — otherwise today's regressed tensors would be selected as tomorrow's reference and mask a real regression. So the three `failed` runs uploaded on 07-07/07-08 can never become the next baseline. The job stays red every night until someone explicitly refreshes the baseline.

The test already supports this: `SGLANG_PRECISION_FORCE_UPDATE=1` skips the comparison and pushes today's tensors as `pass_label="baseline_established"` (`test/registered/debug_utils/test_nightly_precision_regression.py:321,468-481`). It just had no workflow surface to turn it on.

## Fix

Add a boolean `workflow_dispatch` input `force_baseline_update` (default `false`) and plumb it into the precision job env:

```yaml
SGLANG_PRECISION_FORCE_UPDATE: ${{ inputs.force_baseline_update && '1' || '0' }}
```

Scheduled runs are unaffected: under cron, `inputs.force_baseline_update` is empty, so the expression evaluates to `'0'` and normal comparison continues (the test parses `== "1"`).

## Already verified — baseline refreshed on 2026-07-08

To unblock nightly without waiting for this PR to merge (the baseline lives in an external HF dataset, independent of the code repo), the branch was pushed to `sgl-project/sglang` and dispatched once with `force_baseline_update=true` (run 28926436428). Job log confirms the force path was taken:

```
SGLANG_PRECISION_FORCE_UPDATE: 1
[hf-store] baseline_established 264 tensors for zai-org/GLM-5.2-FP8 -> zai-org__GLM-5.2-FP8/2026/07/08/run-6a4673f
zai-org/GLM-5.2-FP8    BASELINE_ESTABLISHED      forced update
Test Summary: 1/1 passed
```

The HF baseline store (`sgl-project/sglang-nightly-precision-baselines`) manifest now ends with a `baseline_established` row (commit `6a4673f`, post-#29783), which is the newest non-`failed` row and will be selected by `_select_latest_run`. The next scheduled nightly compares post-#29783 code against a post-#29783 baseline and goes green; rolling baseline updates resume.

## After merge

Once this PR merges, the `force_baseline_update` input lives on `main`'s workflow, so future dtype/precision changes can be refreshed without pushing a temporary branch:

```
gh workflow run nightly-test-nvidia.yml --repo sgl-project/sglang \
  -f job_filter=nightly-test-precision-8-gpu-h200 \
  -f force_baseline_update=true
```

## Verification

- `pre-commit run --files .github/workflows/nightly-test-nvidia.yml` passes (check-yaml, check-for-duplicate-workflow-job-names, codespell).
- `main` HEAD (`c9303a08da`) contains #29783 (`d8462f4961`).
- Confirmed the test's force-update path pushes `pass_label="baseline_established"` and the store's fetch skips `failed` rows — both observed in the live dispatch above.

















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28930922577](https://github.com/sgl-project/sglang/actions/runs/28930922577)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28930922414](https://github.com/sgl-project/sglang/actions/runs/28930922414)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
