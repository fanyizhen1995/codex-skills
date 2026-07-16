---
source_id: sglang-github-closed-issues-prs
title: Add dummy forward batch preparation hook
canonical_url: https://github.com/sgl-project/sglang/pull/31070
captured_at: '2026-07-14T23:40:21.665711+00:00'
content_hash: 8cca30daf5d39eea8b2ca3cebfe688e521747a746e9129db25847e9b3542f50e
---
# Add dummy forward batch preparation hook

URL: https://github.com/sgl-project/sglang/pull/31070
State: closed
Labels: 
Closed at: 2026-07-14T21:30:32Z
Merged at: 2026-07-14T21:30:32Z

## Summary

- add a no-op `ModelRunner.prepare_dummy_forward_batch` extension point
- invoke it after the runner constructs a dummy batch and before attention metadata initialization

## Motivation

Custom model runners may need to replace or enrich runner-created dummy `ForwardBatch` objects before attention backends inspect them during CUDA graph capture. Keeping the default implementation as an identity function preserves existing behavior while avoiding model-specific imports in the generic runner package.

## Testing

- focused Ruff checks for the changed files
- Python syntax compilation for the changed files





<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29289537343](https://github.com/sgl-project/sglang/actions/runs/29289537343)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29289537172](https://github.com/sgl-project/sglang/actions/runs/29289537172)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
