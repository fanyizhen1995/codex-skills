---
source_id: sglang-github-closed-issues-prs
title: CI Maintenance Mode
canonical_url: https://github.com/sgl-project/sglang/issues/21065
captured_at: '2026-07-13T23:40:05.153791+00:00'
content_hash: 49e2307a91551581d68234efa4172be6a18d95bde9a7ea6814691efc246d1f70
---
# CI Maintenance Mode

URL: https://github.com/sgl-project/sglang/issues/21065
State: closed
Labels: 
Closed at: 2026-04-19T12:32:06Z
Merged at: 

This post introduces a maintenance mode for our CI infrastructure. When the CI is unhealthy (due to too many flaky tests or unstable machines), we will open this issue, and the project will enter CI Maintenance mode.

While maintenance mode is active, normal PRs' CI runs will be paused. Instead, we will allocate all resources to PRs that attempt to fix the CI. Once the CI is healthy and `pr-test.yml` is all green, we will close this issue to declare the end of maintenance mode.

Typically, we will enter the maintenance mode when the scheduled pr-test on main is broken for some consecutive runs
https://github.com/sgl-project/sglang/actions/workflows/pr-test.yml?query=event%3Aschedule


MIN_BASE_SHA: cbcbef6
