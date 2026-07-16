---
source_id: sglang-github-closed-issues-prs
title: Fix avg_request_queue_latency metric not being collected (#6357)
canonical_url: https://github.com/sgl-project/sglang/pull/23735
captured_at: '2026-07-13T23:40:05.177790+00:00'
content_hash: 1b1b72ec5cfc626a4d45ec06488f35e84ed023650872cc45f71ad9ca7dd49b7a
---
# Fix avg_request_queue_latency metric not being collected (#6357)

URL: https://github.com/sgl-project/sglang/pull/23735
State: closed
Labels: 
Closed at: 2026-07-13T18:39:31Z
Merged at: 

## Summary
Adds `sglang:avg_request_queue_latency` Prometheus Gauge that reports average wait time of requests currently in the waiting queue. Updated every stats interval in both prefill and decode reporting paths.

Reopens #20159 (rebased onto current main).

Closes #6357.
