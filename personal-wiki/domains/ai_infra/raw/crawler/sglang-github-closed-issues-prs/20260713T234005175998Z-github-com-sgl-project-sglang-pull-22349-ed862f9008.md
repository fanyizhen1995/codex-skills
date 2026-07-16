---
source_id: sglang-github-closed-issues-prs
title: exit worker nodes when master becomes unreachable (#22227)
canonical_url: https://github.com/sgl-project/sglang/pull/22349
captured_at: '2026-07-13T23:40:05.175998+00:00'
content_hash: ed862f90085a3bccbaf5c6a5ce2dd5b9199eef6df284c1df6920e4530248f26f
---
# exit worker nodes when master becomes unreachable (#22227)

URL: https://github.com/sgl-project/sglang/pull/22349
State: closed
Labels: 
Closed at: 2026-07-13T18:39:36Z
Merged at: 

## Summary
Worker nodes (`node_rank >= 1`) now run a daemon thread that TCP-probes the master's `dist_init_addr` and kills the local process tree after repeated failures, instead of hanging in NCCL forever.

Tunable via `SGLANG_MASTER_WATCHDOG_{INTERVAL,FAILURE_THRESHOLD,STARTUP_GRACE}`. Disable with `SGLANG_DISABLE_MASTER_WATCHDOG=1`.

Closes #22227.
