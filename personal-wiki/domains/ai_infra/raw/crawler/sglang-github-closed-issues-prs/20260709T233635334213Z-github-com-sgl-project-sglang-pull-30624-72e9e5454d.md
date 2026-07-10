---
source_id: sglang-github-closed-issues-prs
title: 'EPLB: rebalance layout logging, dtype-safe dispatch, and misc fixes'
canonical_url: https://github.com/sgl-project/sglang/pull/30624
captured_at: '2026-07-09T23:36:35.334213+00:00'
content_hash: 72e9e5454d56b481ca67cec538bfa533ca082217b42411247069551c86dc2ef9
---
# EPLB: rebalance layout logging, dtype-safe dispatch, and misc fixes

URL: https://github.com/sgl-project/sglang/pull/30624
State: closed
Labels: run-ci
Closed at: 2026-07-09T09:11:07Z
Merged at: 

## Summary

Bundle several EPLB (expert-parallel load balancing) improvements that were developed together.

### Expert-location layout logging
- Add `format_expert_location_layout`, `format_expert_location_layout_diff`, and `format_physical_to_logical_map` in `expert_location.py`. These render the physical-to-logical map per layer and per EP rank in a readable form.
- `EPLBManager` logs the before / target / diff / after layout around a rebalance when `SGLANG_LOG_EXPERT_LOCATION_METADATA` is set.
- `ModelRunner` uses the same formatter for its initial-layout log.

### Dtype-preserving logical→physical dispatch
- The remapped `topk_ids` were only cast back to the input dtype under HIP. Cast whenever the dispatch-map dtype differs from the input dtype instead, and drop the `_is_hip` special case (and the test monkeypatching that depended on it).

### Allow custom routing with expert-location dispatch
- Remove the `assert expert_location_dispatch_info is None` in `select_experts` so a `custom_routing_function` can be combined with expert-location dispatch.

### Expert distribution fixes
- Only route through the select-experts single-pass gatherer for the `deepep` a2a backend; non-deepep and no-a2a paths use the standard topk `select_experts`.
- Track utilization-rate history only when `eplb_min_rebalancing_utilization_threshold != 1.0`.
- Skip empty deques in `_DequeCollection.mean()` to avoid division by zero.
- Remove a stray debug `print`.

### Misc
- Add `SGLANG_SKIP_SGL_KERNEL_VERSION_CHECK` to bypass the kernel-package version checks (flashinfer / sgl-kernel) in `assert_pkg_version` and `check_pkg_version_at_least`.
- Parametrize the EPLB manual test's a2a backend via `SGLANG_EPLB_TEST_MOE_A2A_BACKEND` (defaults to `deepep`, supports `flashinfer`), and add small teardown sleeps.

## Notes

The `expert_location.py` layout-helper block was inserted just after the `ExpertLocationMetadata` class (the module-level global it originally anchored on has since been refactored into `get_resources()`); the code itself is unchanged.

## Original commits

- `8221dd5a04`
- `4e181cde3`
- `e32b85f4b`









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29006476000](https://github.com/sgl-project/sglang/actions/runs/29006476000)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29006475924](https://github.com/sgl-project/sglang/actions/runs/29006475924)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
