---
source_id: sglang-github-closed-issues-prs
title: '[Fix]: Inline H2D during CUDA graph capture to avoid stream isolation in Offloader'
canonical_url: https://github.com/sgl-project/sglang/pull/29166
captured_at: '2026-07-01T02:12:08.952969+00:00'
content_hash: ecdba771c6d75768205620d9b10a1532242f3735e6638ba2de54e1697fc9a615
---
# [Fix]: Inline H2D during CUDA graph capture to avoid stream isolation in Offloader

URL: https://github.com/sgl-project/sglang/pull/29166
State: closed
Labels: run-ci
Closed at: 2026-07-01T00:49:58Z
Merged at: 2026-07-01T00:49:58Z

## Summary

CPU weight offload prefetches parameters on alt_stream and synchronizes via CUDA events. During decode CUDA graph capture, waiting on events recorded on alt_stream (or prefetching there) creates a dependency on uncaptured work and aborts with cudaErrorStreamCaptureIsolation.

When the current stream is capturing, materialize weights inline on the capture stream in start_onload and `wait_and_get_device_tensors` instead of using cross-stream prefetch/wait. Non-capture inference keeps the existing alt_stream overlap path unchanged.

## Root Cause

The CPU offloader pipeline is:
1. At the end of layer `N` forward: `start_onload()` prefetches layer `N + prefetch_step` weights on `alt_stream` and records a CUDA event.
2. At the start of layer `N + prefetch_step` forward: `wait_and_get_device_tensors()` waits on that event, then runs `functional_call` with the GPU weights.

CUDA graph capture only records work on the capture stream. The original code always used `alt_stream` for prefetch and always called `_load_event.wait()` on the capture stream. This violates stream-capture isolation when:
- prefetch is issued on `alt_stream` during capture, or
- a prefetch/event was created during warmup **before** capture starts, and capture later tries to wait on that out-of-capture event.

## Changes

python/sglang/srt/utils/offloader.py

- **_ModuleOffloader.start_onload():** If the current stream is capturing a CUDA graph, load weights inline on the capture stream and skip alt_stream prefetch/event recording. Otherwise, keep the existing async prefetch on alt_stream.

- **_ModuleOffloader.wait_and_get_device_tensors():** If capturing, avoid waiting on _load_event; re-materialize weights inline when a stale pre-capture prefetch exists. Otherwise, wait on _load_event as before.







































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28215099371](https://github.com/sgl-project/sglang/actions/runs/28215099371)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28215099338](https://github.com/sgl-project/sglang/actions/runs/28215099338)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
