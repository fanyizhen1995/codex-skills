---
source_id: sglang-github-closed-issues-prs
title: '[fix] base-a-test-cpu breakage from the flexkv connector (#29701)'
canonical_url: https://github.com/sgl-project/sglang/pull/30375
captured_at: '2026-07-07T23:35:30.909390+00:00'
content_hash: 3be52008e577ce439c9275a7ccdd54b89eb40fc758ec681f801ee06e40d3baa4
---
# [fix] base-a-test-cpu breakage from the flexkv connector (#29701)

URL: https://github.com/sgl-project/sglang/pull/30375
State: closed
Labels: run-ci
Closed at: 2026-07-07T14:16:53Z
Merged at: 

## Summary

#29701 broke two `base-a-test-cpu` shards on main (and every PR's merge-ref CI since):

1. **`test_legacy_global_ratchet.py`** — the new `flexkv_radix_cache.py` calls the legacy `get_global_server_args` shim, growing the ratchet count to 281 > baseline 280. Switch to the `runtime_context.get_server_args()` accessor the ratchet asks for.
2. **`test_registry.py::test_fallback_to_radix_cache`** — the new `enable_flexkv` branch in `default_radix_cache_factory` fires on the test's bare `MagicMock` server_args (auto-attr is truthy) and assigns a MagicMock into `os.environ` → `TypeError: str expected`. Pin `enable_flexkv = False` in `_make_ctx` like the other flags.

## Verification

`test_registry.py` + `test_legacy_global_ratchet.py`: 24 passed locally on this branch; both reproduce the CI failures on current main.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28854200472](https://github.com/sgl-project/sglang/actions/runs/28854200472)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28854200312](https://github.com/sgl-project/sglang/actions/runs/28854200312)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
