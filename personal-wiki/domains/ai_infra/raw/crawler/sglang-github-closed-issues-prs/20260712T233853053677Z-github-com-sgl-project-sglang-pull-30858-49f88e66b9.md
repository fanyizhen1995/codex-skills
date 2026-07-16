---
source_id: sglang-github-closed-issues-prs
title: Fix CUDA 12 Docker dependency resolution
canonical_url: https://github.com/sgl-project/sglang/pull/30858
captured_at: '2026-07-12T23:38:53.053677+00:00'
content_hash: 49f88e66b9ae9a03fd0e5fec9a696ba3572c72b9053901d146a3beab53908485
---
# Fix CUDA 12 Docker dependency resolution

URL: https://github.com/sgl-project/sglang/pull/30858
State: closed
Labels: run-ci, post version patch
Closed at: 2026-07-12T20:50:41Z
Merged at: 2026-07-12T20:50:41Z

## Summary

Pulled this fix out of the PyTorch upgrade PR. Not sure how the CUDA 12 dependency mismatch survived for this long, but this fixes #30856.









































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29149230279](https://github.com/sgl-project/sglang/actions/runs/29149230279)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #29208350188](https://github.com/sgl-project/sglang/actions/runs/29208350188)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
