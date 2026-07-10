---
source_id: sglang-github-closed-issues-prs
title: '[Bugfix] Migrate retired parallel accessors'
canonical_url: https://github.com/sgl-project/sglang/pull/30653
captured_at: '2026-07-09T23:36:35.324761+00:00'
content_hash: b1a3bf7bc0f2bab36f0918e41e9fb3a07756b1bba65b3e6003cf1258a245b323
---
# [Bugfix] Migrate retired parallel accessors

URL: https://github.com/sgl-project/sglang/pull/30653
State: closed
Labels: run-ci
Closed at: 2026-07-09T18:22:35Z
Merged at: 2026-07-09T18:22:35Z

## Summary

Main CI broke from a merge-order mismatch between a few recent PRs.

#30492 and #30493 moved the codebase over to `get_parallel()` and retired the old parallel helper calls. #29421 added the GLM/DSA cache layer-split code while still using the old CP helpers, and #25381 added the GLM Image AR code while still using an old TP helper.

That caused:

- `test_parallel_adoption_ratchet.py` to fail on the legacy getter calls in the DSA layer-split code and the GLM Image AR code
- `test_pool_configurator.py` to fail because `get_attention_cp_size` no longer exists in `dp_attention.py`
- `test_dsa_layer_split_broadcast.py` to still carry the same retired CP helper imports

This updates the DSA layer-split code, its broadcast test helper, and the GLM Image AR code to use the current parallel context fields instead of the retired helpers.

No behavior change intended.

































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29025145148](https://github.com/sgl-project/sglang/actions/runs/29025145148)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29025143974](https://github.com/sgl-project/sglang/actions/runs/29025143974)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
