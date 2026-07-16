---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] model: support Pi0.5'
canonical_url: https://github.com/sgl-project/sglang/pull/30633
captured_at: '2026-07-11T23:37:37.774659+00:00'
content_hash: 4123ffaa7d759bfebd284254c3cc62fb4deb3c3d12f1abc42096c9321ffb1139
---
# [diffusion] model: support Pi0.5

URL: https://github.com/sgl-project/sglang/pull/30633
State: closed
Labels: documentation, dependencies, run-ci, diffusion
Closed at: 2026-07-10T23:50:59Z
Merged at: 2026-07-10T23:50:59Z

## Summary

Adds a native Pi0.5 dVLA action inference path in `multimodal_gen`.

- Adds Pi0.5 pipeline config, VLA sampling params, model registry entries, preprocessing, prefix encoding, action denoising, postprocessing, and action serving endpoints.
- Adds Pi0.5 model components for PaliGemma/SigLIP prefix encoding, Gemma action expert inference, exact full-prefix cache, split prefix/action process-group transport, and denoise CUDA graph runner.
- Serves the generic action API at `/v1/actions/generations`, `/v1/actions/metadata`, and `/v1/actions/realtime`; keeps OpenPI robot clients on `/openpi/policy`.
- Adds guarded Run:ai safetensors streaming support for direct GPU loading.
- Adds the VLA cookbook page, marks Pi0.5 as a dVLA policy, and documents API usage plus VRAM tuning guidance.
- Optimizes grouped multi-camera prefix embedding by batching camera images through one SigLIP forward.

## Current Status

- Golden action GT is now in `sgl-project/ci-data` main at `9982762a42bf2d39ae3a9a78d82b4f04863d35ed`.
- This PR pins `SGL_TEST_FILES_CI_DATA_REVISION` to that ci-data commit and the server consistency test can load the remote GT without `SGLANG_CONSISTENCY_GT_DIR`.
- Validated paths: single GPU HTTP action API, OpenPI websocket smoke, Run:ai direct GPU streaming, and 2-GPU action-SP split.
- Open item: true prefix TP is not complete. A `--tp-size 2 --sp-degree 1` experiment reaches a scheduler/collective gap around prefix execution; do not treat prefix TP as validated in this PR yet. The validated multi-GPU path today is action-SP (`--tp-size 1 --sp-degree 2`).

## Latest Remote Validation

Run on `codex-lingbot-v2-gb300x4`, PR head `ca66c99c29c2`, NVIDIA GB300, `lerobot/pi05_base` / ALOHA profile.

- HTTP consistency: `python3 -m pytest -s python/sglang/multimodal_gen/test/server/test_server_1_gpu.py -k pi05_action_http` passed with remote pinned GT.
- OpenPI websocket smoke passed.
- Run:ai direct GPU streaming was used:
  - 1GPU: streamed 13.5 GiB safetensors directly to CUDA in `0.27s`.
  - 2GPU action-SP: streamed 13.5 GiB per rank directly to CUDA in `1.69s` and `1.34s`.
- Peak reported VRAM during the HTTP perf sweep:
  - 1GPU resident path: up to about `7.59 GiB`.
  - 2GPU action-SP path: root reported about `6.84 GiB`; the action-only rank was resident around `10 GiB` by `nvidia-smi` during the run.

## HTTP Msgpack Performance

Setup: `num_inference_steps=10`, deterministic noise, global prefix cache disabled, 2 warmups, 6 measured repeats, `/v1/actions/generations` with msgpack envelope, server `--batching-max-size 4 --batching-delay-ms 3`.

| Config | Graph | Batch | Single Mean | Single P95 | Batch Mean | Per Request | Preprocess | Prefix | Action Denoise |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1GPU | on | 1 | `81.46 ms` | `82.62 ms` | - | - | `11.30 ms` | `34.17 ms` | `25.92 ms` |
| 1GPU | on | 2 | `86.11 ms` | `105.32 ms` | `120.58 ms` | `60.29 ms` | `11.92 ms` | `40.54 ms` | `23.17 ms` |
| 1GPU | on | 4 | `79.19 ms` | `81.22 ms` | `130.18 ms` | `32.55 ms` | `11.60 ms` | `34.50 ms` | `23.09 ms` |
| 1GPU | off | 1 | `300.70 ms` | `306.03 ms` | - | - | `11.23 ms` | `36.10 ms` | `243.03 ms` |
| 1GPU | off | 2 | `291.33 ms` | `296.04 ms` | `325.41 ms` | `162.70 ms` | `11.37 ms` | `34.76 ms` | `235.05 ms` |
| 1GPU | off | 4 | `294.54 ms` | `299.56 ms` | `434.60 ms` | `108.65 ms` | `12.04 ms` | `34.65 ms` | `236.98 ms` |
| 2GPU action-SP | on | 1 | `115.70 ms` | `128.76 ms` | - | - | `16.02 ms` | `37.89 ms` | `42.22 ms` |
| 2GPU action-SP | on | 2 | `133.28 ms` | `135.58 ms` | `248.47 ms` | `124.23 ms` | `16.24 ms` | `54.12 ms` | `42.33 ms` |
| 2GPU action-SP | on | 4 | `128.63 ms` | `136.28 ms` | `488.70 ms` | `122.18 ms` | `17.41 ms` | `48.24 ms` | `42.36 ms` |
| 2GPU action-SP | off | 1 | `609.92 ms` | `644.64 ms` | - | - | `16.33 ms` | `45.04 ms` | `527.35 ms` |
| 2GPU action-SP | off | 2 | `611.54 ms` | `653.89 ms` | `1199.55 ms` | `599.77 ms` | `16.58 ms` | `42.57 ms` | `530.99 ms` |
| 2GPU action-SP | off | 4 | `531.64 ms` | `604.13 ms` | `2333.31 ms` | `583.33 ms` | `16.25 ms` | `36.56 ms` | `458.41 ms` |

Key takeaways from this sweep:

- CUDA graph is the main serving-path speedup: 1GPU batch=1 improves from `300.70 ms` to `81.46 ms`; batch=4 per-request improves from `108.65 ms` to `32.55 ms`.
- For current Pi0.5, 2GPU action-SP is slower than 1GPU because the action expert and horizon are small enough that SP/Ulysses communication dominates. It remains an expansion path for larger future action experts, not the default for Pi0.5.
- The default recommended Pi0.5 serving path remains single-GPU resident bf16 + action CUDA graph + dynamic batching.

## Precision / Correctness Checks

- LeRobot reference parity: one-step velocity max absolute difference `1.17e-6`; final 10-step action max absolute difference `1.17e-7`.
- OpenPI-compatible precision: SGLang runtime reports `3,233,713,264` bf16 parameters and `119,720,608` fp32 parameters after skipping unused LM heads; output actions are float32.
- Exact full-prefix cache: first prefix pass about `203 ms`; exact cache hit prefix stage about `0.2 ms`.
- 2-GPU action-SP smoke returned action shape `[50, 32]`; output matched single-GPU HTTP with max absolute difference `0` in the previous split validation.
- 16GB-free pressure check completed without OOM on the resident bf16 no-offload path; latency should still be re-measured on the actual target edge device.

## Screenshots

cookbook:
<img width="302" height="361" alt="image" src="https://github.com/user-attachments/assets/819d8e91-f75f-4d0b-82b1-05380a63baca" />




inference architecture:
<img width="1672" height="941" alt="image" src="https://github.com/user-attachments/assets/fe254f61-4d14-4b29-8ba8-a487c1675974" />





































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29100589465](https://github.com/sgl-project/sglang/actions/runs/29100589465)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29100588385](https://github.com/sgl-project/sglang/actions/runs/29100588385)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
