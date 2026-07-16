---
source_id: sglang-github-closed-issues-prs
title: Use int32 for KV cache index tensors (#17649)
canonical_url: https://github.com/sgl-project/sglang/pull/19860
captured_at: '2026-07-13T23:40:05.172384+00:00'
content_hash: ab5219faa5ca906be24930f9f93f361ae0eccd6f445bffa03b59a797cfc4df8c
---
# Use int32 for KV cache index tensors (#17649)

URL: https://github.com/sgl-project/sglang/pull/19860
State: closed
Labels: 
Closed at: 2026-07-13T18:39:44Z
Merged at: 

## Summary

KV cache allocators created index tensors as int64 which were then explicitly cast to int32 at usage sites. Since cache indices never exceed int32 range, changed allocators to produce int32 from the start and removed all downstream casts.

Closes #17649
