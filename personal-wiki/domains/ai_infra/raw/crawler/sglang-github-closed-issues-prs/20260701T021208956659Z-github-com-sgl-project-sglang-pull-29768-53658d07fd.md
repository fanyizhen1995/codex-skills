---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Stop rocm720 pr auto-runs'
canonical_url: https://github.com/sgl-project/sglang/pull/29768
captured_at: '2026-07-01T02:12:08.956659+00:00'
content_hash: 53658d07fd47135e6a089e2156d3fad5e8c1005d516c63a478e6ae095a93a358
---
# [AMD] Stop rocm720 pr auto-runs

URL: https://github.com/sgl-project/sglang/pull/29768
State: closed
Labels: amd
Closed at: 2026-06-30T15:58:25Z
Merged at: 2026-06-30T15:58:25Z

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28457066015](https://github.com/sgl-project/sglang/actions/runs/28457066015)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28457064738](https://github.com/sgl-project/sglang/actions/runs/28457064738)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
