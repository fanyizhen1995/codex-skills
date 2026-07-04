---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] Prefer official diffusion consistency GT'
canonical_url: https://github.com/sgl-project/sglang/pull/29831
captured_at: '2026-07-04T02:13:49.128529+00:00'
content_hash: 1dc595f7443b37032e4b7fd633cff7e52e31a380d4f829d09908c9049a1daced
---
# [diffusion] Prefer official diffusion consistency GT

URL: https://github.com/sgl-project/sglang/pull/29831
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-04T02:09:33Z
Merged at: 2026-07-04T02:09:33Z

## Summary

- Prefer `official_generated` remote consistency GT when it exists in `ci-data`.
- Fall back to `sglang_generated` when the official GT is missing.
- Keep Ascend-specific GT lookup ahead of the default directories and cover the selection order in unit tests.





















































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28690414072](https://github.com/sgl-project/sglang/actions/runs/28690414072)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28690414003](https://github.com/sgl-project/sglang/actions/runs/28690414003)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
