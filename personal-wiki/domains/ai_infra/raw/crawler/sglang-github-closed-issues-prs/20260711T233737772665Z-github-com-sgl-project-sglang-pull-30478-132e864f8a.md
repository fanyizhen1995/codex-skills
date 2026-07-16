---
source_id: sglang-github-closed-issues-prs
title: Add DCP to runtime parallel context
canonical_url: https://github.com/sgl-project/sglang/pull/30478
captured_at: '2026-07-11T23:37:37.772665+00:00'
content_hash: 132e864f8a23a0324e71c1aa2925f496224c3431a5639b187be463e928bc2d6e
---
# Add DCP to runtime parallel context

URL: https://github.com/sgl-project/sglang/pull/30478
State: closed
Labels: deepseek, run-ci, bypass-fastfail
Closed at: 2026-07-11T04:23:42Z
Merged at: 2026-07-11T04:23:42Z

## Summary

Add decode context parallelism (DCP) to `get_parallel()` so runtime-context consumers can read DCP topology through the same structured accessor used for TP, PP, MoE, and attention parallelism.

## Changes

- Add `dcp_size`, `dcp_rank`, and `dcp_group` to `ParallelContext`.
- Delegate those properties live to `parallel_state.get_dcp_world_size()`, `get_dcp_rank()`, and `get_dcp_group()`.
- Include DCP fields in `get_parallel().override(...)` validation.
- Extend `test/registered/unit/test_runtime_context.py` delegation tables to cover the new DCP size/rank/group accessors.

## Validation

- `python3 -m py_compile python/sglang/srt/runtime_context.py test/registered/unit/test_runtime_context.py`
- Import-light DCP accessor harness covering `dcp_size`, `dcp_rank`, `dcp_group`, and override restoration.
- Commit hooks passed: Python AST, `isort`, `ruff`, `black-jupyter`, `codespell`, and CI registry validation.

Local full unit entrypoint was blocked in this desktop Python environment because importing `sglang` requires `orjson`, which is not installed here:

```text
ModuleNotFoundError: No module named 'orjson'
```

I will trigger `test/registered/dcp/test_dsv31_dcp8_gsm8k.py` via `/rerun-test` for PR validation.

















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29129817862](https://github.com/sgl-project/sglang/actions/runs/29129817862)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29129817814](https://github.com/sgl-project/sglang/actions/runs/29129817814)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
