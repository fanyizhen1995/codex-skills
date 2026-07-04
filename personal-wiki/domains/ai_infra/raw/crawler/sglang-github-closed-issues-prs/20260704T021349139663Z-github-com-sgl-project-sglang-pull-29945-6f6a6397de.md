---
source_id: sglang-github-closed-issues-prs
title: Move deferred mamba cow and clear
canonical_url: https://github.com/sgl-project/sglang/pull/29945
captured_at: '2026-07-04T02:13:49.139663+00:00'
content_hash: 6f6a6397de79aea5861b928ba1ce99cb9dc9fda44874cc6bb0f2f59116ba5cf6
---
# Move deferred mamba cow and clear

URL: https://github.com/sgl-project/sglang/pull/29945
State: closed
Labels: run-ci, bypass-fastfail, run-ci-extra
Closed at: 2026-07-03T03:29:05Z
Merged at: 2026-07-03T03:29:05Z

## Motivation

The deferred mamba COW and clear are mamba-pool operations but currently live on the linear attention backend. This moves them into `ModelRunner._forward_raw`, where the forward already owns the pool, so they no longer depend on the attention backend.



































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28607680895](https://github.com/sgl-project/sglang/actions/runs/28607680895)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28607680676](https://github.com/sgl-project/sglang/actions/runs/28607680676)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
