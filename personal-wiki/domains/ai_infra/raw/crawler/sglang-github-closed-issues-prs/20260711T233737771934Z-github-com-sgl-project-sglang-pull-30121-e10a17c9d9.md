---
source_id: sglang-github-closed-issues-prs
title: '[Apple Silicon] [CI] Move the MLX lane to the check-changes + pr-gate composite'
canonical_url: https://github.com/sgl-project/sglang/pull/30121
captured_at: '2026-07-11T23:37:37.771934+00:00'
content_hash: e10a17c9d9134847e514db914bfaa4010e939b19224862cb5fe687b7212cd059
---
# [Apple Silicon] [CI] Move the MLX lane to the check-changes + pr-gate composite

URL: https://github.com/sgl-project/sglang/pull/30121
State: closed
Labels: quant, run-ci, apple-silicon
Closed at: 2026-07-11T05:00:15Z
Merged at: 2026-07-11T05:00:15Z

## Motivation

#29691 landed the MLX lane (`pr-test-mlx.yml`) with standalone gating. This PR began as a migration to the shared check-changes plus pr-gate composite used by the other hardware lanes. Implementations include: a separate `sgl_kernel` filter output following `_pr-test-check-changes.yml`, and a staged layout aligned with the other backends, wired for the smoke tests from #29440. All three are in this PR, so it is a gate migration plus a staged restructure. Per @yeahdongcn's review, the scope is inclusive of moving stage A onto `run_suite.py` suite registration, matching how every other hardware lane selects its tests instead of an explicit file list.

## Modifications

Gate migration

- A dorny/paths-filter `check-changes` job plus the reusable `pr-gate` workflow replace the inline label gate. `pr-gate` live fetches labels at runtime, so adding `run-ci` and rerunning failed jobs restores the suite. The old frozen
  payload gate never could.
- The workflow level permissions block is removed; it zeroed the `pull-requests` and `actions` scopes the paths filter and the gate API reads require. The vendor lanes running this same chain declare no block.

Filter split

- `main_package` and `sgl_kernel` are separate filter outputs, following `_pr-test-check-changes.yml`; the `sgl_kernel` glob is copied verbatim from that file. `pr-gate` keys off a `changes_exist` aggregate, matching the MUSA and NPU lanes.
- Stage A gates on `main_package` or `sgl_kernel`, matching the base stages of `pr-test.yml`, so the trigger surface is unchanged from the single key filter.

Staged layout and #29440 wiring

- `mlx-unit-test` becomes `stage-a-unit-test-mlx`. Invocation, env, and runner are unchanged: model free unit tests, `HF_HUB_OFFLINE=1`, GitHub hosted `macos-26`.
- A new `stage-b-e2e-test-mlx` job is defined for the #29440 smoke tests: served correctness for qwen2_moe and qwen3_moe plus the reference equivalence test. Those tests load 8 GB to 17 GB models and are tuned for 24 GB of unified memory; GitHub hosted `macos-26` runners have 7 GB. Stage B therefore activates only through a `workflow_dispatch` `target_stage` input until a self hosted Apple Silicon runner registers. The mechanism is copied from the MUSA lane, with two corrections to make dispatch functional. Stage B currently has no scheduled execution; it fires only via the constrained dispatch input, pending the self hosted runner.
- `workflow_dispatch` with a `target_stage` input is added for per stage dispatch; the input is a constrained `type: choice` following the AMD lane (a free text field, per the MUSA original, silently no-ops on a typo).
- The finish job adopts the MUSA pattern: iterate over `needs`, fail on failure or cancellation, tolerate skipped.

Test registration

- Stage A now runs via `python3 run_suite.py --hw mlx --suite stage-a-unit-test-mlx` instead of an explicit pytest file list, matching how the XPU lane invokes `run_suite.py`. This adds `HWBackend.MLX` and `register_mlx_ci()` to the shared `ci_register.py`, plus a `stage-a-unit-test-mlx` entry in `run_suite.py`'s per-commit suites.
- `test_quantization.py` mixed a model-free class (`TestMlxQuantizationOverride`, previously cherry-picked via `pytest ::ClassName`) with a model-downloading class (`TestMlxQuantization`) in one file. `run_suite.py` only runs whole files, so `TestMlxQuantizationOverride` moves to its own file, `test_mlx_quantization_override.py`, registered for both `base-a-test-cpu` and the new MLX suite. `test_quantization.py` keeps only the model-dependent class, now registered under `stage-b-e2e-mlx` (it performs real HF loads, so it belongs with the gated model requiring suite rather than stage-a).
- Test registration is now structural: a new model-free MLX unit test file registers itself with `register_mlx_ci(...)`, the same pattern every other backend uses, instead of a line in the workflow's explicit list.
- A review pass surfaced three MLX test files whose assertions had never executed in any CI configuration (CPU registered with MLX skip guards: skipped on Linux, invisible to the MLX suite). `test_mlx_pool_dtype.py` and `test_tp_worker_routing.py` now run in stage-a (verified green under the lane's exact env locally); `test_quantization.py` reclassified to stage B as above.

Dependencies and deferrals

- #29440 has been merged, the referenced files exist on main, and the stage now awaits only the self-hosted runner.
- Shares the `register_mlx_ci` marker with #29804 (byte identical `ci_register.py` addition; merges cleanly in either order).

## Accuracy Tests

CI only change; no model or kernel behavior affected. The `FakeOverlapScheduler` stub desync from #29217 (AttributeError on `forward_ct`) is fixed on main via #30125, and stage A is expected green against the merge commit.

## Speed Tests and Profiling

N/A.





<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28996751813](https://github.com/sgl-project/sglang/actions/runs/28996751813)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28996751681](https://github.com/sgl-project/sglang/actions/runs/28996751681)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
