---
source_id: sglang-github-closed-issues-prs
title: '[Kernel] Hotfix: update sgl-kernel imports of relocated fp8_kernel (RFC #29630
  #30784)'
canonical_url: https://github.com/sgl-project/sglang/pull/31089
captured_at: '2026-07-14T23:40:21.689829+00:00'
content_hash: e876182b8be53e448150dba68f3525510c534ad1b045bc03315862b604ba05be
---
# [Kernel] Hotfix: update sgl-kernel imports of relocated fp8_kernel (RFC #29630 #30784)

URL: https://github.com/sgl-project/sglang/pull/31089
State: closed
Labels: quant, sgl-kernel, run-ci
Closed at: 2026-07-14T00:41:23Z
Merged at: 2026-07-14T00:41:23Z

## Problem

RFC #29630 Phase 2.5 PR #30784 relocated `fp8_kernel` from
`sglang.srt.layers.quantization.fp8_kernel` → `sglang.kernels.ops.quantization.fp8_kernel`
(move + rewrite all imports, **no compatibility shim**).

The import rewrite covered `python/sglang/`, `test/` and `benchmark/`, but **missed the
`sgl-kernel/` subtree**. Three `sgl-kernel` test/benchmark modules still import the old
path, so after #30784 merged they fail at collection with:

```
ModuleNotFoundError: No module named 'sglang.srt.layers.quantization.fp8_kernel'
```

This breaks the **`Run sgl-kernel unit tests on B200`** job on `main` for every PR (e.g. it
surfaced on an unrelated PR's CI), not just the migration PRs.

## Fix

Rewrite the three stale imports to the new path:

| File | lines |
|------|-------|
| `sgl-kernel/tests/test_per_token_group_quant_8bit.py` | 14, 17 |
| `sgl-kernel/benchmark/bench_per_token_group_quant_8bit.py` | 11, 14, 17 |
| `sgl-kernel/benchmark/bench_fp8_blockwise_gemm.py` | 23 |

`sglang.srt.layers.quantization.fp8_kernel` → `sglang.kernels.ops.quantization.fp8_kernel`

All imported symbols — `per_token_group_quant_8bit`, `sglang_per_token_group_quant_8bit`,
`w8a8_block_fp8_matmul_triton`, `create_per_token_group_quant_fp8_output_scale` — exist at
the new path (the relocation was byte-identical). Pure import-path change, no behavior change.

Verified: no `srt.layers.quantization.fp8_kernel` references remain anywhere in `sgl-kernel/`,
and a repo-wide sweep confirms these three were the only stale old-path Python imports left
(the other relocated quant modules — int8_kernel / mxfp8 / awq / nvfp4 — have no old-path
consumers in the skipped dirs).

🤖 Generated with [Claude Code](https://claude.com/claude-code)













<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29296300849](https://github.com/sgl-project/sglang/actions/runs/29296300849)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29296408618](https://github.com/sgl-project/sglang/actions/runs/29296408618)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
