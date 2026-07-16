---
source_id: sglang-github-closed-issues-prs
title: Add DCP to runtime parallel context
canonical_url: https://github.com/sgl-project/sglang/pull/30831
captured_at: '2026-07-10T23:37:20.318278+00:00'
content_hash: 141954e5dc3e4b31d3ca0325d9eb533f1a86bcf5cee216e58d46b81d28691692
---
# Add DCP to runtime parallel context

URL: https://github.com/sgl-project/sglang/pull/30831
State: closed
Labels: deepseek
Closed at: 2026-07-10T23:07:16Z
Merged at: 

## Summary

Rebased continuation of #30478 onto latest `main`.

Main already exposes `dcp_size` / `dcp_rank` / `dcp_group` on `ParallelContext`. This PR completes the DCP surface and migrates in-tree readers:

- Add `dcp_enabled`, `attn_dcp_size`, and `attn_dcp_rank` to `ParallelContext`
- Migrate in-tree DCP call sites to `get_parallel()`
- Keep `layers.dcp` accessors as deprecated compatibility shims for out-of-tree callers
- Update the parallel-adoption ratchet and unit coverage

Path note vs the original PR: `mla_buffer` now lives under `python/sglang/kernels/ops/kvcache/` (renamed on main after #30478 was opened).

Original author: @Fridge003 (from #30478).

## Why a new PR?

#30478 is from `Fridge003/sglang` with `maintainer_can_modify=false`, so the rebased history could not be force-pushed onto the original head. Once this lands, #30478 can be closed.

## Validation

- `python3 -m py_compile` on touched modules
- `pytest test/registered/unit/test_runtime_context.py` — 62 passed
- `pytest test/registered/unit/test_parallel_adoption_ratchet.py` — 1 passed

## Related

- Supersedes #30478















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29129817862](https://github.com/sgl-project/sglang/actions/runs/29129817862)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:hourglass_flowing_sand: [Run #29129817814](https://github.com/sgl-project/sglang/actions/runs/29129817814)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
