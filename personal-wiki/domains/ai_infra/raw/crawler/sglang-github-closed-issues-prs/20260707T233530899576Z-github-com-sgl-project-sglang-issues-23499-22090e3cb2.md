---
source_id: sglang-github-closed-issues-prs
title: Segfault in NIXL UCX worker during disaggregated KV transfer
canonical_url: https://github.com/sgl-project/sglang/issues/23499
captured_at: '2026-07-07T23:35:30.899576+00:00'
content_hash: 22090e3cb200d234aeeff836f4a288f70f908fa43622e5358a7bcd18554cab26
---
# Segfault in NIXL UCX worker during disaggregated KV transfer

URL: https://github.com/sgl-project/sglang/issues/23499
State: closed
Labels: 
Closed at: 2026-05-18T10:55:07Z
Merged at: 

## Summary
Segmentation fault in `nixlUcxSharedThread::run()` -> `ucp_worker_arm()` -> `uct_cuda_base_iface_event_fd_arm` when transferring KV chunks from prefill to decode workers in disaggregated serving.

## Error
```
!!!!!!! Segfault encountered !!!!!!!
  File "<unknown>", line 0, in gsignal
  File "<unknown>", line 0, in cuEventQuery
  File "<unknown>", line 0, in uct_cuda_base_iface_event_fd_arm
  File "<unknown>", line 0, in ucp_worker_arm
  File "<unknown>", line 0, in nixlUcxSharedThread::run()
  File "<unknown>", line 0, in 0xffffffffffffffff
```

Full traceback in `inkwell-copper-cn01_prefill_w0.out`:
- `prefill.py:828` in `send_kv_chunk`
- `conn.py:645` in `send_aux` (NIXL UCX transfer call)
- `prefill.py:540` in `process_batch_result_disagg_prefill`
- `scheduler.py:2950` in `process_batch_result`
- `prefill.py:454` in `event_loop_overlap_disagg_prefill`

## Job Context
- **Job**: `dsr1-fp8-1k1k-ultra-tpt-24803056480` (job ID 4707)
- **Model**: deepseek-ai/DeepSeek-R1, FP8 precision
- **Topology**: Disaggregated prefill+decode, 2 prefill nodes + 2 decode nodes, EP=8, TP=8, DP=8
- **Config**: `disaggregation-transfer-backend: nixl`
- **Time of crash**: ~21:30:19 UTC, ~2 minutes into benchmark run
- **Crash context**: ~1850 pending tokens, 2015 queued requests, processing batches normally before crash

## Timestamps
- `21:30:19.856` — Last normal batch: `#new-seq: 16, #new-token: 15744`
- `21:30:19.870` — Segfault fires
- `21:30:21` — Scheduler subprocess exits with SIGQUIT (code -3)
- `21:30:27` — srtctl detects prefill_0 exit code 137 (SIGKILL from parent)

## Consequent Errors (not causal)
After the segfault, Gloo broadcasts fail with "Connection closed by peer" — this is because the scheduler process crashed, not the cause.
Decode workers then fail to reach bootstrap on port 30001 — also consequential.

## Suspect Commits
No recent sglang commits directly touch the NIXL UCX code path. The crash is in the `nixl_cu13` binary extension (UCX-based NIXL transport), which is a separate build artifact. The crash location `uct_cuda_base_iface_event_fd_arm` is inside UCX's CUDA memory interface.

Relevant recent disagg-related commits:
- `0d040527`: Fix for `_commit_transfer_to_req()` NVLink issue (mooncake path, not NIXL)
- `fe9b9b25`: Fix segfault in `cudaMemcpyBatchAsync` on CUDA 13.0 (not NIXL UCX)

## Suggested Fix
1. Verify NIXL `nixl_cu13` wheel version and check if newer version fixes UCX CUDA event handling
2. Investigate whether `disaggregation-transfer-backend` can use an alternative backend (e.g., mooncake) as a workaround
3. Examine UCX env vars (`UCX_TLS`, `UCX_CUDA_MANAGER`) for potential stabilization
4. If no workaround: the sglang team should add validation/guards around the NIXL UCX async event handling in high-throughput disagg scenarios, or consider alternative transport implementations
