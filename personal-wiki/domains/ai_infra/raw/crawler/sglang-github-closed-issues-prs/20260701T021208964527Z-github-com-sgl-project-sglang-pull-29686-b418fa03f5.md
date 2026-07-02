---
source_id: sglang-github-closed-issues-prs
title: Update GLM tests to 5.2 and delete redundant tests
canonical_url: https://github.com/sgl-project/sglang/pull/29686
captured_at: '2026-07-01T02:12:08.964527+00:00'
content_hash: b418fa03f56479cdf41464186bb90d7ebb57a698b007a88b03177c0719ef4ee8
---
# Update GLM tests to 5.2 and delete redundant tests

URL: https://github.com/sgl-project/sglang/pull/29686
State: closed
Labels: deepseek, blackwell
Closed at: 2026-06-30T06:04:27Z
Merged at: 2026-06-30T06:04:27Z

## Summary
- Remove the requested CUDA DeepSeek V3.2 nightly/e2e test registrations and files.
- Remove the GB300 GLM FP8 nightly test and its stale suite entry.
- Update remaining CUDA GLM FP8/NVFP4 tests to use GLM-5.2 checkpoints.

## Validation
- `python3 -m compileall -q test/run_suite.py test/registered/8-gpu-models/test_glm_51_fp8.py test/registered/cuda_graph/piecewise/test_pcg_glm5_fp8_tp8.py test/registered/cuda_graph/piecewise/test_pcg_glm5_fp4.py test/registered/gb300/test_glm5_nvfp4.py test/registered/debug_utils/test_nightly_precision_regression.py test/registered/radix_cache/unified_radix_tree/test_unified_radix_cache_kl_nightly.py test/registered/models_e2e/test_dsa_glm5_dp_mtp.py test/registered/models_e2e/test_dsa_glm5_hisparse.py test/registered/models_e2e/test_dsa_glm5_tp_mtp.py`
- Registry parser check for all modified CUDA test files
- `python3 scripts/ci/check_registered_tests.py`
- Pre-commit hooks during `git commit`

































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28417762324](https://github.com/sgl-project/sglang/actions/runs/28417762324)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28417762243](https://github.com/sgl-project/sglang/actions/runs/28417762243)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
