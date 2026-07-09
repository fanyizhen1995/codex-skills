---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Register 2 hardware-agnostic 1-GPU PR tests for AMD CI'
canonical_url: https://github.com/sgl-project/sglang/pull/30207
captured_at: '2026-07-08T23:36:33.797904+00:00'
content_hash: 7d78df675d94b4343a508e8eb3c852d4939c3125f60472c063be04b70e5fb87e
---
# [AMD] Register 2 hardware-agnostic 1-GPU PR tests for AMD CI

URL: https://github.com/sgl-project/sglang/pull/30207
State: closed
Labels: lora, run-ci
Closed at: 2026-07-07T21:46:23Z
Merged at: 2026-07-07T21:46:23Z

## Motivation

Closes part of the AMD-vs-NVIDIA per-commit (PR-tier) coverage gap tracked on
the ROCm CI dashboard. Both tests already run on NVIDIA per-commit CI
(`base-b` 1-GPU) but had no `register_amd_ci(...)`. Both are hardware-agnostic
(mock-model engine test / pure-Triton kernel) and pass unchanged on ROCm.

## Modifications

`register_amd_ci(...)` added next to the existing `register_cuda_ci(...)`
(CUDA `base-b` → AMD `stage-b`):

| File | AMD suite | est | What it covers |
|---|---|---|---|
| [unit/managers/test_customized_info_streaming.py](https://github.com/sgl-project/sglang/blob/main/test/registered/unit/managers/test_customized_info_streaming.py) | `stage-b-test-1-gpu-small-amd` | 120 | Mock model (dummy weights), `skip_tokenizer_init`, `disable_cuda_graph`; scheduler → tokenizer-manager → Engine streaming path |
| [lora/test_moe_lora_info.py](https://github.com/sgl-project/sglang/blob/main/test/registered/lora/test_moe_lora_info.py) | `stage-b-test-1-gpu-small-amd` | 5 | Pure Triton kernel (`_compute_moe_lora_info`) validated against a plain-torch reference |

### Dropped after CI verification

Two FP8 tests originally included were **verified failing** on the AMD lane and
removed (kept CUDA-only). Documented as AMD-excluded on the dashboard in
ROCm/sglang-ci#311:
- `moe/test_triton_moe_channel_fp8_kernel.py` — per-channel FP8 fused_moe, 7/8 pass; one config exceeds ROCm tolerance.
- `quant/test_fp8_kernel.py` — FP8 quant numerics diverge on ROCm.

## Test plan — verified on BOTH AMD lanes

| File | rocm700 (MI325, `pr-test-amd`) | rocm720 (ROCm 7.2.0, `pr-test-amd-rocm720`) |
|---|---|---|
| `test_customized_info_streaming.py` | ✅ 54s | ✅ 38s |
| `test_moe_lora_info.py` | ✅ 7s | ✅ 7s |

- rocm700: https://github.com/sgl-project/sglang/actions/runs/28817203900
- rocm720: https://github.com/sgl-project/sglang/actions/runs/28894524624 (completed `success`)

- [x] AMD CI passes on the registered files — **rocm700 + rocm720**
- [x] NVIDIA CI green (registration-only change; PR merged)
