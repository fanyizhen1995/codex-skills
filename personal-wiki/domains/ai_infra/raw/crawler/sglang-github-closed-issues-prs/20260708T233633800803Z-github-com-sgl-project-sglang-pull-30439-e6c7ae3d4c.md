---
source_id: sglang-github-closed-issues-prs
title: Fix FA3 prefill CP NaNs
canonical_url: https://github.com/sgl-project/sglang/pull/30439
captured_at: '2026-07-08T23:36:33.800803+00:00'
content_hash: e6c7ae3d4ce01540814f92b72d15e12d2357a3cc839cb9ad81902bc75cf1bed4
---
# Fix FA3 prefill CP NaNs

URL: https://github.com/sgl-project/sglang/pull/30439
State: closed
Labels: 
Closed at: 2026-07-08T03:16:09Z
Merged at: 2026-07-08T03:16:09Z

## Summary

Fix the FA3 prefill-CP burst NaN/IMA failure seen with Qwen3 MoE, zigzag CP, and GQA-style mixed prefix-hit/long-prefill batches.

Changes:
- Disable FA3 scheduler metadata precompute when prefill CP is enabled with `attn_cp_size > 1`, matching the existing distributed-attention safety path.
- Keep zigzag CP-v2 out of `ForwardMode.MIXED`, which the zigzag split metadata does not support safely.
- Clear stale CP-v2 metadata when the eager runner falls back to the normal non-CP-v2 path.
- Add focused CP unit coverage for the FA3 metadata guard and `MIXED` rejection.

## Root Cause

The burst repro failed in FA3 split-KV combine with stale precomputed scheduler metadata while live CP/decode metadata changed `cache_seqlens`/`num_splits` across ranks. Leaving `scheduler_metadata` unset makes FA3 use the existing per-layer metadata path and avoids the OOB combine access.

I also checked the suspected `merge_state` path and the zigzag padding comment from PR #28421. The merge-state changes were reverted, and the H200 devbox validation restored the pre-fix `common_ops.abi3.so` before rerunning the burst. The linked padding concern still looks like a separate CP-v2/GQA safety item, but it was not needed to fix this burst repro.

## Validation

Local/static:
- `python3 -m py_compile python/sglang/srt/layers/attention/flashattention_backend.py python/sglang/srt/layers/cp/zigzag.py python/sglang/srt/model_executor/runner/eager_runner.py test/registered/cp/test_cp_strategy_unit.py`
- `git diff --check`
- pre-commit hooks during commit

On `4_H200` devbox `baizhou-dev`:
- `python3 -m pytest test/registered/cp/test_cp_strategy_unit.py -q` -> 11 passed
- `python3 -m pytest sgl-kernel/tests/test_merge_state_v2.py -q` -> 150 passed
- no-CP-v2 8-sequence burst repro, 96 rounds -> clean log, no NaN/assert/illegal/CUDA-error signatures
- `SGLANG_ENABLE_CP_V2=1` 8-sequence burst repro, 96 rounds -> clean log, no NaN/assert/illegal/CUDA-error signatures



































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28912543941](https://github.com/sgl-project/sglang/actions/runs/28912543941)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28912543801](https://github.com/sgl-project/sglang/actions/runs/28912543801)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
