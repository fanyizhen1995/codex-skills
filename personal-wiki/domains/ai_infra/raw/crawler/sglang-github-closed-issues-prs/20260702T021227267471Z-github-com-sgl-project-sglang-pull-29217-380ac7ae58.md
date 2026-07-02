---
source_id: sglang-github-closed-issues-prs
title: '[MLX] Fix step-bounded profiling for bench tools on Apple Silicon'
canonical_url: https://github.com/sgl-project/sglang/pull/29217
captured_at: '2026-07-02T02:12:27.267471+00:00'
content_hash: 380ac7ae58a68a858260dd7f105dfdc451cb1933c50627a3c155845a07c924f2
---
# [MLX] Fix step-bounded profiling for bench tools on Apple Silicon

URL: https://github.com/sgl-project/sglang/pull/29217
State: closed
Labels: 
Closed at: 2026-07-01T05:55:30Z
Merged at: 2026-07-01T05:55:30Z

## Motivation

Part of the Apple Device Support roadmap (#19137), Profiling section. Follow-up to #28122.

On the MLX backend, `bench_offline_throughput`, `bench_one_batch_server`, and `bench_serving` could not produce usable Apple-native Metal traces. Step-bounded profiling never auto-stopped, so a `--profile` run tried to GPU-capture the entire generation. Under `MTL_CAPTURE_ENABLED=1` this is far slower, so the scheduler watchdog (300s) fired and SIGQUIT-killed the server before the trace was finalized.

## Root cause

The MLX overlap loop (`event_loop_overlap_mlx`) bypasses `Scheduler.run_batch()`, which is where `forward_ct` is incremented and `SchedulerProfilerManager._profile_batch_predicate()` is called. As a result, on MLX `forward_ct` never advanced, so (a) the watchdog liveness counter was permanently stalled and (b) the profiler's step-based auto-stop never triggered.

## Modifications

- `scheduler_mixin.py`: advance `forward_ct` and call the profiler batch predicate once per finalized forward step in `_finalize_mlx_pending_job`, mirroring `run_batch()`. This is what makes `--profile-steps` (and the server `/start_profile` num_steps path) actually take effect on the MLX overlap loop.
- `benchmark/offline_throughput.py`: make the post-run `stop_profile()` idempotent (catch the "not in progress" `RuntimeError`). With `--profile-steps N` the scheduler auto-stops mid-run, but a run shorter than N steps never reaches the target and would otherwise hang in `monitor_trace_file` (which loops with no timeout).
- Add unit test `test/registered/unit/hardware_backend/mlx/test_scheduler_mixin.py`.

## Accuracy Tests

N/A — scheduler bookkeeping + benchmark CLI only. `SGLANG_PROFILE_V2` defaults to False, so the predicate is a no-op during normal inference, and `forward_ct` does not affect model outputs.

## Speed Tests and Profiling

Negligible: one integer increment + a no-op predicate call per forward step.

Verified on Apple M-series (Qwen2.5-0.5B, MTL_CAPTURE_ENABLED=1): all three tools auto-stop after N steps and finalize a .gputrace cleanly, no watchdog crash.

## Checklist

- [x] Format your code according to the Format code with pre-commit.
- [x] Add unit tests according to the Run and add unit tests.
