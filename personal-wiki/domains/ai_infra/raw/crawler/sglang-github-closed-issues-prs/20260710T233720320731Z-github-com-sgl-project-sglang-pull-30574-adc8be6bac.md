---
source_id: sglang-github-closed-issues-prs
title: '[kv canary] Support UnifiedRadixCache in kv-canary and bracket nested model.forward'
canonical_url: https://github.com/sgl-project/sglang/pull/30574
captured_at: '2026-07-10T23:37:20.320731+00:00'
content_hash: adc8be6bacbca1d97f2cdcb5426a75de06a75cafb58477f5f6f892458c40fa85
---
# [kv canary] Support UnifiedRadixCache in kv-canary and bracket nested model.forward

URL: https://github.com/sgl-project/sglang/pull/30574
State: closed
Labels: run-ci, run-ci-extra
Closed at: 2026-07-10T17:58:56Z
Merged at: 2026-07-10T17:58:56Z

## Motivation

kv-canary's radix-cache walker currently only supports `RadixCache` and `SWARadixCache`, and its `model.forward` patch runs pre/post ops unconditionally. This breaks two cases:

1. Running kv-canary with `UnifiedRadixCache` raises `NotImplementedError`.
2. Models that enter a second patched `model.forward` from inside the top-level forward (e.g. a vision-language model calling its inner language model) trigger a second pre-op before the first post-op, tripping the phase checker.

## Changes

- **`radix_cache_walker.py`**: add `UnifiedRadixCache` support. Node slots/lengths are read from the base component's data, unlocked-ness from the base component's `lock_ref`, and SWA residency from the SWA component when it is present in `tree_components`.
- **`canary_manager.py`**: add `model_forward_bracket_scope()`, a reentrancy guard that reports whether the current patched `model.forward` is the outermost call.
- **`api.py`**: use the bracket scope so only the outermost `model.forward` runs the kv-canary pre/post ops; nested calls delegate straight to the original forward.
- **`base_runner.py`**: run the FlashInfer autotune dummy forward inside the canary's active single-forward-manager context so bracketing works during autotune.

## Notes

The `base_runner.py` hunk was adapted to the current upstream structure: autotune now runs the dummy forward through a `forward_fn` closure passed to `run_flashinfer_autotune_forward`, so the canary run context is built once and threaded into `_dummy_run(run_ctx=...)` inside that closure. `run_flashinfer_autotune_forward` invokes `forward_fn` exactly once, so the context manager is entered only once.

## Original commits

- `cd6ba6b90`































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29061372388](https://github.com/sgl-project/sglang/actions/runs/29061372388)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29061372337](https://github.com/sgl-project/sglang/actions/runs/29061372337)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
