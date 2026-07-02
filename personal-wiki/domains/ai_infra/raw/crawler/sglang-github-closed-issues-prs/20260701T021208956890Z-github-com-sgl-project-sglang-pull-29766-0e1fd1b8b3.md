---
source_id: sglang-github-closed-issues-prs
title: 'ci: stop automatic ROCm 7.2 PR runs'
canonical_url: https://github.com/sgl-project/sglang/pull/29766
captured_at: '2026-07-01T02:12:08.956890+00:00'
content_hash: 0e1fd1b8b3d6c66ee4018f2aac827dbd1fd76f4dc8f55c099df21d9f7a85d5e6
---
# ci: stop automatic ROCm 7.2 PR runs

URL: https://github.com/sgl-project/sglang/pull/29766
State: closed
Labels: amd
Closed at: 2026-06-30T15:57:52Z
Merged at: 

## Summary
- Comment out the `pull_request` trigger for `pr-test-amd-rocm720.yml` so the workflow does not auto-run on every matching PR.
- Keep the PR trigger block in place as comments so it can be re-enabled later.
- Give scheduled ROCm 7.2 runs unique concurrency groups and only allow cancellation for `pull_request` events, preventing schedule runs from cancelling each other.
- Refresh comments that still described PR behavior.

## Testing
- `git diff --check`
- Verified the active `pull_request` trigger is absent, the commented block remains, schedule/workflow_dispatch/workflow_call remain enabled, and schedule concurrency uses `github.run_id`.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28456713652](https://github.com/sgl-project/sglang/actions/runs/28456713652)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28456713536](https://github.com/sgl-project/sglang/actions/runs/28456713536)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
