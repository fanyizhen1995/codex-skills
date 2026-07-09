---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Register 2 CPU-bound 1-GPU tests (phase_checker, scripted_runtime_core)
  for AMD PR CI'
canonical_url: https://github.com/sgl-project/sglang/pull/30446
captured_at: '2026-07-08T23:36:33.788413+00:00'
content_hash: 015d5b37b25bec3ffd70edd120a231a2313783d3d8a28b7f7fc77e71146bf19b
---
# [AMD] Register 2 CPU-bound 1-GPU tests (phase_checker, scripted_runtime_core) for AMD PR CI

URL: https://github.com/sgl-project/sglang/pull/30446
State: closed
Labels: 
Closed at: 2026-07-08T21:04:24Z
Merged at: 2026-07-08T21:04:24Z

## What
Register 2 CPU-bound NVIDIA-only per-commit tests for AMD 1-GPU PR CI. Both already run on NVIDIA per-commit and use generic torch/device ops or CPU-only logic, so adding `register_amd_ci(...)` next to `register_cuda_ci(...)` is sufficient.

| File | AMD suite | est_time | Why safe on AMD |
|------|-----------|---------:|-----------------|
| `utils/test_phase_checker.py` | `stage-b-test-1-gpu-small-amd` | 120 | `SimplePhaseChecker` device-tensor + subprocess tests; plain `torch.device` ops, no CUDA-only deps |
| `scripted_runtime/test_scripted_runtime_core.py` | `stage-b-test-1-gpu-small-amd` | 460 | Scripted-runtime core logic; no CUDA-only imports / `.cuda()`-only paths |

Standard 2-line edit per file: add `register_amd_ci(...)` alongside `register_cuda_ci(...)` (cuda-style `stage=`/`runner_config=` shape with `-amd` appended).

## Validation (dispatched on upstream — both AMD lanes green)
- ROCm 7.0.0 (mi3xx) `stage-b-test-1-gpu-small-amd`: ✅ https://github.com/sgl-project/sglang/actions/runs/28907747528
- ROCm 7.2.0 `stage-b-test-1-gpu-small-amd-rocm720`: ✅ (all 14 partitions) https://github.com/sgl-project/sglang/actions/runs/28918550073

### Dropped (real ROCm gap)
`model_loading/test_utils_update_weights.py` was initially included but **dropped** — its engine fixture imports `torch_memory_saver`, which isn't available on ROCm (`ModuleNotFoundError` at setup, [failed run](https://github.com/sgl-project/sglang/actions/runs/28907748539)). Left CUDA-only rather than register-and-skip.

## Test plan
- [x] AMD `stage-b-test-1-gpu-small-amd` green (mi3xx)
- [x] rocm720 lane green
- [ ] NVIDIA CI unchanged
