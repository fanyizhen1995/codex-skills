---
source_id: sglang-github-closed-issues-prs
title: Preserve RMSNorm shape in batch-invariant mode
canonical_url: https://github.com/sgl-project/sglang/pull/30956
captured_at: '2026-07-13T23:40:05.194611+00:00'
content_hash: 1a52c7178dfb8e82ffa239612b6b27bb16fbb3cd8ea59f624669fb21d69fa297
---
# Preserve RMSNorm shape in batch-invariant mode

URL: https://github.com/sgl-project/sglang/pull/30956
State: closed
Labels: run-ci
Closed at: 2026-07-13T00:51:54Z
Merged at: 2026-07-13T00:51:54Z

## Summary

- Restore the original higher-rank output shape after the batch-invariant RMSNorm path.
- Add a regression test for a 3D RMSNorm input.

## Adaptations

- Updated the regression test to use the current runtime context server-args override API.

## Testing

- `python3 -m py_compile python/sglang/srt/layers/layernorm.py test/registered/unit/batch_invariant_ops/test_batch_invariant_ops.py`
- `git diff --check`
- `with-proxy uv run pre-commit run --files python/sglang/srt/layers/layernorm.py test/registered/unit/batch_invariant_ops/test_batch_invariant_ops.py`
- `.venv/bin/python -m pytest test/registered/unit/batch_invariant_ops/test_batch_invariant_ops.py -k rmsnorm_preserves_higher_rank_shape -q`

## Original commits

- `0ae28b8c45`











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29216197644](https://github.com/sgl-project/sglang/actions/runs/29216197644)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29216197540](https://github.com/sgl-project/sglang/actions/runs/29216197540)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
