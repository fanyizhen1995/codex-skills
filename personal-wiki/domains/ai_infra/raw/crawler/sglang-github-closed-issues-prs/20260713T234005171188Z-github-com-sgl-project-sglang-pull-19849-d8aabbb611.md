---
source_id: sglang-github-closed-issues-prs
title: Add request_id metadata to MoE expert distribution output (#17774)
canonical_url: https://github.com/sgl-project/sglang/pull/19849
captured_at: '2026-07-13T23:40:05.171188+00:00'
content_hash: d8aabbb611809df6517d11913fe7eb0aa34a963cfc74020b36c113570930e204
---
# Add request_id metadata to MoE expert distribution output (#17774)

URL: https://github.com/sgl-project/sglang/pull/19849
State: closed
Labels: 
Closed at: 2026-07-13T18:39:47Z
Merged at: 

## Summary

MoE expert distribution logs lacked request IDs, making per-request debugging impossible. Threaded request_id from ForwardBatch through all gatherer types to the distribution output.

Closes #17774
