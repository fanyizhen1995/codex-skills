---
source_id: sglang-github-closed-issues-prs
title: Fix SHM feature finalization under DP attention
canonical_url: https://github.com/sgl-project/sglang/pull/29536
captured_at: '2026-06-29T04:09:41.035309+00:00'
content_hash: 2a367a5a11294e591878bc3bfcf2bdb99c8863dd3ceda44a788817794fdd9033
---
# Fix SHM feature finalization under DP attention

URL: https://github.com/sgl-project/sglang/pull/29536
State: closed
Labels: run-ci
Closed at: 2026-06-28T05:24:51Z
Merged at: 

## Summary
- Synchronize on the CPU groups that broadcast SHM-backed multimodal work requests before materializing and unlinking those features.
- Preserve the existing TP-group barrier behavior for the non-DP-attention path.
- Add focused unit coverage for DP-attention, non-DP-attention, and no-SHM finalization behavior.

## Testing
- uv run python -m py_compile python/sglang/srt/managers/scheduler_components/request_receiver.py test/registered/unit/managers/test_request_receiver_shm_finalize.py
- uv run python -m pytest test/registered/unit/managers/test_request_receiver_shm_finalize.py (could not run locally: pytest is not installed in this environment)

## Source commits
- `5058b632`







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28308122067](https://github.com/sgl-project/sglang/actions/runs/28308122067)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28308122022](https://github.com/sgl-project/sglang/actions/runs/28308122022)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
