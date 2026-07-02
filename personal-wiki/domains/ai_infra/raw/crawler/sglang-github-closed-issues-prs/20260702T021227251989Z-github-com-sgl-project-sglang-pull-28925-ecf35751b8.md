---
source_id: sglang-github-closed-issues-prs
title: 'fix(nightly-precision): pin flashinfer allreduce-fusion backend for TP-partial
  capture contract'
canonical_url: https://github.com/sgl-project/sglang/pull/28925
captured_at: '2026-07-02T02:12:27.251989+00:00'
content_hash: ecf35751b85a8e5ab6021153aa03f42531a3699a2050ddcf059c1da4525c8ade
---
# fix(nightly-precision): pin flashinfer allreduce-fusion backend for TP-partial capture contract

URL: https://github.com/sgl-project/sglang/pull/28925
State: closed
Labels: 
Closed at: 2026-07-02T00:26:19Z
Merged at: 2026-07-02T00:26:19Z

## Problem

The nightly precision regression test (`test_nightly_precision_regression`, suite `nightly-precision-8-gpu-h200`) has been failing on `zai-org/GLM-5.1-FP8` since 2026-06-17:

```
FAILED - tensor=non_intrusive__model.layers.8.inputs.1 rel_diff=0.7537
```

30/33 captured layers fail, all with `rel_diff` in `[0.7497, 0.7839]`. Only layer 0 passes.

## Root cause

Bisected to #23402 (`32685874f3`, "Reenable MNNVL backend for FlashInfer allreduce fusion"). That PR correctly dropped SM90 from the fusion auto-enable list (SM90 mnnvl needs an NVLink multicast fabric H200 nodes do not reliably have), changing the gate on H200 from `enable_flashinfer_allreduce_fusion` (auto True for GLM-family) to `flashinfer_allreduce_fusion_backend is not None` (None on H200).

The nightly serve flags pass no fusion flag, so fusion is now OFF where it used to be ON. This flips the dumper capture contract:

- fusion ON (#23402 before): the previous MLP layer skips `postprocess_layer` and tags the tensor for deferred allreduce, so the dumper pre-hook at the next layer entry captures a TP-partial sum (ranks differ).
- fusion OFF (#23402 after): the previous layer allreduces immediately, so the dumper captures an identical full sum on every rank.

The comparator compares with `--override-dims "...:bs h[tp:partial]"`, whose `tp:partial` is a ReduceSum (`torch.stack(ranks).sum(0)`). Summing 8 identical full-sum tensors yields 8x the baseline (partial-sum) magnitude — abs_mean 0.00556 -> 0.04443, exactly 8x — and `rel_diff = 1 - 16/65 = 0.7538`, matching the observed 0.7537.

Layer 0 passes because `inputs.1` of layer 0 is the embedding output, before any MLP allreduce.

## Fix

- Pin `--flashinfer-allreduce-fusion-backend=trtllm` in the nightly serve flags so the dumper captures TP-partial sums again (the comparator contract). Explicit `trtllm`, not `auto`, because `auto` resolves to `mnnvl` on SM90 single-node.
- Include the fusion backend in the capture signature so a future change to the fusion default re-establishes the baseline (first run) instead of silently mismatching partial vs full tensors.

This is a test-infra capture-contract fix, not a forward-precision change: the model forward is unchanged, only which tensor (partial vs full) the dumper records. The fused H200 GLM path is what the existing baselines and comparator dims were built for.

## Verification

E2E on an H200 devbox (8xH200, TP8, main worktree, GLM-5.1-FP8):

- Served with the nightly flags + `--flashinfer-allreduce-fusion-backend=trtllm`. Chat returned 200; dumper captured 1872 tensors (78 layers x 8 ranks x 3 steps).
- Ran the nightly comparator against the 2026-06-16 HF baseline (run-2dd449c, pre-#23402 partial-sum): **33/33 passed, max_rel_diff=0.000000** — bit-exact match. This confirms the fix restores the pre-#23402 capture contract (TP-partial), so the existing baseline is reusable.
- Causal chain confirmed: with the flag, `flashinfer_allreduce_fusion_backend` resolves to `trtllm` and `apply_flashinfer_allreduce_fusion(bs)` returns `True`; without it, the backend is `None` and it returns `False`.
- Historical HF baseline data corroborates the regression: 2026-06-16 (pre-#23402) baseline layer 8 abs_mean=0.00556 (partial); 2026-06-17/22 target abs_mean=0.04443 = 8x, rel_diff=0.7537.
- `pre-commit` (black/isort/ruff/clang-format) passes; `py_compile` passes.

## Related

- #28190 fixes `_select_latest_run` to not promote failed runs to the comparison baseline. That bug caused 2026-06-20/21 to pass falsely (the 06-19 failed full-sum run became the baseline). It is independent of this fix but should land together so failed runs can no longer mask this class of regression.
