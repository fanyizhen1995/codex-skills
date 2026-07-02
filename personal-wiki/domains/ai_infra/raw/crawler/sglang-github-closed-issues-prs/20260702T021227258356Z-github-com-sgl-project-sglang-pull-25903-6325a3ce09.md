---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] Async output finalization'
canonical_url: https://github.com/sgl-project/sglang/pull/25903
captured_at: '2026-07-02T02:12:27.258356+00:00'
content_hash: 6325a3ce09e10154c7075cf4306f5e89fa96d1f35e21667e87ded1dedab795a8
---
# [diffusion] Async output finalization

URL: https://github.com/sgl-project/sglang/pull/25903
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-01T14:44:34Z
Merged at: 

## Summary

- Adds adaptive async output finalization for eligible diffusion file-path outputs.
- Keeps isolated single requests on the synchronous save path: no background save submit, no output-save future, no future wait.
- Enables async save only when the scheduler/client observes overlapping generation work, so queued/burst requests can overlap file encode/write with later work.
- Scope is limited to monolithic, non-CPU, file-path-only outputs without frame interpolation or upscaling.

## Implementation

- `Req.allow_async_output_save` defaults to `False`.
- `Scheduler` marks queued generation bursts for async output save.
- `AsyncSchedulerClient` marks same-tick concurrent HTTP forwards before serialization, preserving burst behavior for concurrent HTTP requests.
- `GPUWorker` checks `allow_async_output_save` before async-save capability checks. False-hint requests directly use the synchronous save path.
- The async path intentionally pre-materializes frames before submitting the save task, then offloads file encode/write. A follow-up profile showed that moving CUDA-to-CPU materialization into the background thread worsens tail latency and should not be merged.

## Validation

Current PR head: `f64163f86f12e7c4327553c4de4ee604228c33ca`.

- `pre-commit run --files python/sglang/multimodal_gen/runtime/managers/gpu_worker.py python/sglang/multimodal_gen/runtime/managers/scheduler.py python/sglang/multimodal_gen/runtime/scheduler_client.py python/sglang/multimodal_gen/test/unit/test_async_output_save.py`
- Remote unit test: `PYTHONPATH=/sgl-workspace/sglang/python python3 -m pytest -q python/sglang/multimodal_gen/test/unit/test_async_output_save.py` -> `8 passed`

## Full-Server Request Matrix: Three-Way Rerun

This is the stricter real HTTP request validation. It compares no-async baseline, the previous always-async behavior, and this PR on the same devbox/GPU.

Setup:

- GPU: 1x B200
- Server: `--batching-max-size 4 --batching-delay-ms 5 --num-gpus 1`
- Baseline/no-async: `c6a7c98ae4`
- Always-async: `8095abebbc`
- PR/adaptive: `f64163f86f`

| model case | request mode | baseline | always-async | PR |
| --- | --- | ---: | ---: | ---: |
| Z-Image-Turbo 1024 url, 4 steps | single p50 | 0.442 s | 0.451 s | 0.441 s |
| Z-Image-Turbo 1024 url, 4 steps | c8 makespan p50 | 2.478 s | 2.474 s | 2.466 s |
| Wan2.1 T2V 1.3B 832x480 17f, 4 steps | single p50 | 2.005 s | 2.005 s | 2.006 s |
| Wan2.1 T2V 1.3B 832x480 17f, 4 steps | c4 makespan p50 | 5.017 s | 5.021 s | 5.018 s |

Interpretation:

- The stricter same-GPU three-way full-server rerun does not show a material real HTTP E2E speedup for either the measured image or video case.
- For the Z-Image case, all c8 makespan deltas are below `0.5%`.
- For the Wan2.1 17f case, baseline, always-async, and PR all land around `5.02s` c4 makespan.
- Do not claim real E2E speedup from this PR. The defensible claim is narrower: single requests avoid async/future overhead, queued synthetic workloads can benefit, and the measured real HTTP image/video cases are neutral.

## Output-Finalization Critical-Path Profile

This profile isolates CUDA-to-CPU/frame materialization from local encode/write, and compares the current PR boundary with an experimental variant that also offloads materialization.

Setup:

- GPU: 1x B200
- PR head: `f64163f86f`
- `current_async`: current PR behavior, pre-materialize frames on the worker path and offload encode/write.
- `full_materialize_offload`: experimental patch that moves raw tensor materialization into the background save thread.

| model case | variant | single p50 | single p95 | concurrent makespan p50 | concurrent makespan p95 | pre-materialize p50 | async save task p50 | encode/write p50 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Z-Image-Turbo 1024 url, 4 steps | current_async | 0.444 s | 0.447 s | 2.485 s | 2.498 s | 0.83 ms | 41.8 ms | 8.4 ms |
| Z-Image-Turbo 1024 url, 4 steps | full_materialize_offload | 0.442 s | 1.303 s | 2.530 s | 3.738 s | n/a | 540.2 ms | 3.2 ms |
| Wan2.1 T2V 1.3B 832x480 49f, 4 steps | current_async | 3.007 s | 3.008 s | 10.023 s | 10.026 s | 65.7 ms | 1.742 s | 471.1 ms |
| Wan2.1 T2V 1.3B 832x480 49f, 4 steps | full_materialize_offload | 3.007 s | 3.007 s | 10.026 s | 10.026 s | n/a | 2.466 s | 469.3 ms |

Interpretation:

- CUDA-to-CPU/frame materialization remains on the critical path in the current PR, but it is small for image and tens of milliseconds for 49-frame video.
- Local video encode/write is the actual large cost: about `0.47s` p50 per 49-frame mp4, and about `1.74-2.04s` per 4-output dynamic batch in the background task.
- Moving raw tensor materialization into the background thread is not worth merging. It significantly worsens image tail latency and makes the video background task longer without improving E2E makespan.
- The current PR boundary is the right one: offload only the expensive and overlapable encode/write portion, not CUDA-to-CPU materialization.
- Cloud upload is separate API-layer work. It is awaited when S3 storage is enabled because response URL semantics may depend on it, so it is intentionally not folded into this worker-level async-save PR.

## Synthetic Scheduler Matrix: No-Async Baseline vs PR

This matrix is not a real HTTP/model-server request benchmark. It is a scheduler-level synthetic workload used to isolate output tensor size, save/finalization cost, and scheduler overlap behavior.

Setup:

- GPU: 1x B200
- Benchmark: fake generation plus CUDA fp16 video tensors and real `GPUWorker._save_output_paths()`
- Baseline: `c6a7c98ae4` with no async output finalization
- PR: `f64163f86f`
- Small tensor: `480p24f`, raw fp16 `54.8 MB`, materialized uint8 `27.4 MB`
- Large tensor: `720p48f`, raw fp16 `253.1 MB`, materialized uint8 `126.6 MB`
- Single req: p50 over 20 isolated synthetic requests
- Multi req: 8 queued synthetic requests, 500ms simulated generation per request, total makespan

| request mode | tensor size | baseline | PR | PR / baseline | result |
| --- | --- | ---: | ---: | ---: | --- |
| single req | small tensor | 683.199 ms | 688.619 ms | 1.0079x | neutral; no async/future path |
| single req | large tensor | 918.768 ms | 922.575 ms | 1.0041x | neutral; no async/future path |
| multi req | small tensor | 5.452 s | 4.235 s | 0.7768x | 1.29x faster |
| multi req | large tensor | 7.500 s | 4.749 s | 0.6332x | 1.58x faster |

## Synthetic Burst Guardrail: Always-Async vs PR

This is also scheduler-level synthetic data. It checks that the adaptive policy does not materially lose the burst benefit of the original always-async implementation.

| request mode | tensor size | always-async | PR | PR / always-async |
| --- | --- | ---: | ---: | ---: |
| multi req | small tensor | 4.234 s | 4.235 s | 1.0004x |
| multi req | large tensor | 4.663 s | 4.749 s | 1.0185x |

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28463113171](https://github.com/sgl-project/sglang/actions/runs/28463113171)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28463113008](https://github.com/sgl-project/sglang/actions/runs/28463113008)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
