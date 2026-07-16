---
source_id: sglang-github-closed-issues-prs
title: Improve EPLB dispatch handling and diagnostics
canonical_url: https://github.com/sgl-project/sglang/pull/30646
captured_at: '2026-07-10T23:37:20.320980+00:00'
content_hash: 725f2e3c7453e52506548a14e07f5f51b6dd6f1a13e25910957f3d71f8b51b65
---
# Improve EPLB dispatch handling and diagnostics

URL: https://github.com/sgl-project/sglang/pull/30646
State: closed
Labels: run-ci
Closed at: 2026-07-10T17:40:20Z
Merged at: 2026-07-10T17:40:20Z

## Summary

- Improve EPLB single-pass gatherer selection for non-DeepEP A2A backends and custom routing paths.
- Add expert-location layout formatting and rebalance diagnostics behind the existing logging control.
- Preserve dispatch index dtype when remapping logical expert ids to physical ids, and update the CPU coverage.
- Allow selected kernel package version checks to be bypassed through the existing environment control.

## Testing

- `python3 -m py_compile python/sglang/srt/eplb/eplb_manager.py python/sglang/srt/eplb/expert_distribution.py python/sglang/srt/eplb/expert_location.py python/sglang/srt/eplb/expert_location_dispatch.py python/sglang/srt/layers/moe/topk.py python/sglang/srt/model_executor/model_runner.py python/sglang/srt/utils/common.py test/registered/unit/eplb/test_dispatch_dtype_preservation.py`
- `with-proxy uv run pytest test/registered/unit/eplb/test_dispatch_dtype_preservation.py`
- `with-proxy uv run pre-commit run --files python/sglang/srt/eplb/eplb_manager.py python/sglang/srt/eplb/expert_distribution.py python/sglang/srt/eplb/expert_location.py python/sglang/srt/eplb/expert_location_dispatch.py python/sglang/srt/layers/moe/topk.py python/sglang/srt/model_executor/model_runner.py python/sglang/srt/utils/common.py test/registered/unit/eplb/test_dispatch_dtype_preservation.py`

## Original commits

- `4e181cde38`
- `e32b85f4bb`













































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29061382724](https://github.com/sgl-project/sglang/actions/runs/29061382724)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29061382549](https://github.com/sgl-project/sglang/actions/runs/29061382549)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
