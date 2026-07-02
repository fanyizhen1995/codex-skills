---
source_id: sglang-github-closed-issues-prs
title: '[CI] Migrate JIT tests missed by #29066 to runner_config registration'
canonical_url: https://github.com/sgl-project/sglang/pull/29715
captured_at: '2026-07-01T02:12:08.963792+00:00'
content_hash: e1f3be1f2bb22cc6c3f723175a415134897ae47edeaf7b5ca9ff946f90f5783a
---
# [CI] Migrate JIT tests missed by #29066 to runner_config registration

URL: https://github.com/sgl-project/sglang/pull/29715
State: closed
Labels: quant
Closed at: 2026-06-30T06:21:15Z
Merged at: 2026-06-30T06:21:15Z

## Summary

#29066 migrated the PR-test JIT kernel suites from the legacy `suite=` string to explicit `stage=`/`runner_config=` metadata, and **renamed** those suites to the generated `<stage>-test-<runner_config>` form (note the `-test-` infix that `effective_suite` produces). The `pr-test-jit-kernel.yml` workflow was updated to invoke the renamed suites (`base-b-kernel-unit-test-1-gpu-large`, etc.).

That migration sweep was frozen on #29066's last code commit (2026-06-26), but the PR didn't merge until 2026-06-30. During that ~4-day review window, **9 other JIT-kernel PRs merged to main**, each registering with the old `suite="base-b-kernel-..."` convention. Because the squash merge only applies the recorded diff (it doesn't re-sweep main), those newly-added files were never converted.

As a result, their `effective_suite` stayed in the old no-`-test-` shape (e.g. `base-b-kernel-unit-1-gpu-large`) and **no longer matches any suite the workflow invokes — so they were silently dropped from PR CI.**

## Fix

**1. Migrate the missed registrations** to `stage=`/`runner_config=`. Nightly/AMD registrations (e.g. `nightly-kernel-1-gpu`) are intentionally left on the legacy `suite=` form — that's still the supported shape for suites that don't follow `{stage}-test-{runner_config}`.

⚠️ The **three B200 registrations** additionally pointed at the now-removed `1-gpu-b200` runner; they're repointed at the standardized `4-gpu-b200` used by every other migrated B200 test (the only B200 job the workflow defines).

**2. Close the validator hole that allowed this.** `scripts/ci/check_registered_tests.py` (the `check-registered-tests` pre-commit hook, also enforced in `lint.yml`) only rejected legacy `suite=` of the `{stage}-test-{runner_config}` shape — it matched names containing `-test-`, so the *old* dead shape (`base-b-kernel-unit-1-gpu-large`, no `-test-`) slipped through. Tighten it: a CUDA registry may keep the legacy single-string `suite=` **only** for the nightly/stress/weekly families; any other CUDA `suite=` must use the modern form. This fails a non-dispatchable suite name at pre-commit/CI regardless of merge ordering, so a stale PR can no longer reintroduce this bug.

**3. Re-home a mis-categorized test the guard surfaced.** `test/registered/dcp/test_reduce_scatter_along_dim.py` registered `base-b-kernel-unit-8-gpu-h200` — but it isn't a kernel test: it checks `GroupCoordinator.reduce_scatter_along_dim` (a `parallel_state` device-comm wrapper) against `torch.distributed.reduce_scatter_tensor`, with no `jit_kernel`/`sgl_kernel` import. #29066 missed it because it lives outside `test/registered/jit/`, and it was silently dropped too. Moved it to `stage="extra-b"` / `runner_config="8-gpu-h200"` — same 8×H200 runner, but the correct workflow (`pr-test-extra.yml`), matching its `dcp/` sibling `test_dsv31_dcp8_gsm8k.py` and the `cp/pp/ep` distributed-test convention.

### JIT files migrated, by resolved suite

**`base-b-kernel-unit` / `1-gpu-large`**
- `test/registered/jit/test_dsv3_router_gemm.py` (#21531)
- `test/registered/jit/test_dsv3_fused_a_gemm.py` (#27397)
- `test/registered/jit/test_cutedsl_dsv3_fused_a_gemm.py` (#27397)
- `test/registered/jit/test_dsv32_indexer_fusion.py` (#27705)
- `test/registered/jit/test_sparse_mla_q8kv8_prefill_sm90.py` (#25751)
- `test/registered/jit/diffusion/test_causal_conv3d_cat_pad.py` (#29281)
- `test/registered/jit/diffusion/test_residual_gate_add.py` (#29361)
- `test/registered/jit/diffusion/test_ltx2_ada_values.py` (#29390)

**`base-b-kernel-unit` / `8-gpu-h200`**
- `test/registered/jit/test_symm_mem_all_gather.py` (#29223)

**`base-b-kernel-unit` / `4-gpu-b200`** (was the removed `1-gpu-b200`)
- `test/registered/jit/test_silu_and_mul_scaled_fp4_experts_quant_packed.py` (#18612)
- `test/registered/jit/diffusion/test_causal_conv3d_cat_pad.py` (#29281)
- `test/registered/jit/diffusion/test_residual_gate_add.py` (#29361)

**`base-b-kernel-benchmark` / `1-gpu-large`**
- `test/registered/jit/benchmark/bench_dsv3_fused_a_gemm.py` (#27397)
- `test/registered/jit/benchmark/bench_dsv3_router_gemm.py` (#21531)
- `test/registered/jit/benchmark/bench_sparse_mla_q8kv8_prefill_sm90.py` (#25751)
- `test/registered/jit/benchmark/bench_symm_mem_all_gather.py` (#29223)
- `test/registered/jit/benchmark/diffusion/bench_causal_conv3d_cat_pad.py` (#29281)
- `test/registered/jit/benchmark/diffusion/bench_residual_gate_add.py` (#29361)

### Re-homed (not a kernel test)
- `test/registered/dcp/test_reduce_scatter_along_dim.py` (#14194): `base-b-kernel-unit-8-gpu-h200` → `extra-b` / `8-gpu-h200`

## Test plan
- `python3 scripts/ci/check_registered_tests.py` → exit 0 on the full tree.
- Regression-checked the strengthened guard: reintroducing an old-shape `base-…` suite makes it exit 1 with the offending file listed.
- Parsed each edited file via `ut_parse_one_file` and confirmed `effective_suite` resolves to the suites the workflows invoke (`base-b-kernel-*-test-*` for the JIT files; `extra-b-test-8-gpu-h200` for the re-homed comm test), while nightly registrations are unchanged.
- `/rerun-test test/registered/jit/*` to exercise the re-dispatched 1-gpu/b200 JIT tests on CI.

🤖 Generated with [Claude Code](https://claude.com/claude-code)





















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28424359118](https://github.com/sgl-project/sglang/actions/runs/28424359118)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28424358988](https://github.com/sgl-project/sglang/actions/runs/28424358988)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
