---
source_id: sglang-github-closed-issues-prs
title: '[multimodal] Add SM120 Triton attention backend'
canonical_url: https://github.com/sgl-project/sglang/pull/29803
captured_at: '2026-07-02T02:12:27.258072+00:00'
content_hash: 4914f16e3a3613c8ced6b80204e0484c9f7e881ef01c2218f8d355a130782e4b
---
# [multimodal] Add SM120 Triton attention backend

URL: https://github.com/sgl-project/sglang/pull/29803
State: closed
Labels: diffusion
Closed at: 2026-07-01T15:15:03Z
Merged at: 

## Motivation
Diffusion currently falls back to Torch SDPA on SM120 consumer Blackwell GPUs because FlashAttention is unavailable in this build. This PR exposes an explicit `sm120_triton_attn` backend that reuses SRT's Triton extend-attention kernel path and its SM120 block-size tuning.

## Changes
- Add `AttentionBackendEnum.SM120_TRITON_ATTN` and wire it through CUDA backend selection with an SM12.x hardware guard.
- Allow DiT configs to opt into `sm120_triton_attn`.
- Add a diffusion attention backend wrapper using `extend_attention_fwd(skip_prefix=True)` for dense self-attention and Torch SDPA fallback for non-CUDA or cross-attention cases.
- Add unit coverage for CLI/backend selection and a 5090-only benchmark test that compares `sm120_triton_attn` with `torch_sdpa`.

## Validation
- `pre-commit run --files python/sglang/multimodal_gen/configs/models/dits/base.py python/sglang/multimodal_gen/runtime/platforms/cuda.py python/sglang/multimodal_gen/runtime/platforms/interface.py python/sglang/multimodal_gen/runtime/layers/attention/backends/sm120_triton_attn.py python/sglang/multimodal_gen/test/single_test_file/test_sm120_triton_attention_perf.py python/sglang/multimodal_gen/test/unit/test_sm120_triton_attention_backend.py`
- 5090 availability passed on rerun `28492645908`, job `84452380959`: `1 passed, 21 warnings in 11.44s`.
- 5090 benchmark rerun `28493302466` failed during checkout because it used an old SHA, so I reran the measurements on a real 5090 devbox at PR head `2d5afdee1a571c9855232b4d5f66f1be4b7ff2d0`.
- Environment: `NVIDIA GeForce RTX 5090`, driver `580.105.08`, `torch 2.11.0+cu130`.
- FlashAttention check: `from flash_attn import flash_attn_func` failed on this image; requesting `fa` on SM120 is expected to fall back to `torch_sdpa`.

### 5090 micro attention benchmark

BF16 dense self-attention, non-causal, head_dim=128. `speedup_vs_sdpa < 1` means `sm120_triton_attn` is slower than Torch SDPA.

| shape `(B,S,H,D)` | `sm120_triton_attn` ms | `torch_sdpa` ms | speedup vs SDPA | max abs diff vs SDPA | mean abs diff vs SDPA | p99 abs diff vs SDPA |
|---|---:|---:|---:|---:|---:|---:|
| `(1,512,24,128)` | 0.063 | 0.039 | 0.62x | 0.001953 | 7.53e-05 | 0.000488 |
| `(1,1024,24,128)` | 0.137 | 0.111 | 0.81x | 0.001953 | 8.15e-05 | 0.000488 |
| `(1,2048,24,128)` | 0.433 | 0.322 | 0.74x | 0.000977 | 6.10e-05 | 0.000488 |
| `(1,4096,24,128)` | 1.669 | 1.055 | 0.63x | 0.000977 | 4.47e-05 | 0.000244 |
| `(1,8192,24,128)` | 7.028 | 4.171 | 0.59x | 0.000488 | 3.24e-05 | 0.000244 |
| `(1,2048,40,128)` | 0.685 | 0.430 | 0.63x | 0.001953 | 6.10e-05 | 0.000488 |
| `(1,4096,40,128)` | 2.734 | 1.691 | 0.62x | 0.000977 | 4.47e-05 | 0.000244 |
| `(1,8192,40,128)` | 12.672 | 6.695 | 0.53x | 0.000977 | 3.24e-05 | 0.000244 |

Small-shape math-SDPA reference:

| shape `(B,S,H,D)` | SDPA math ms | `sm120` mean abs diff vs math | `torch_sdpa` mean abs diff vs math |
|---|---:|---:|---:|
| `(1,512,24,128)` | 0.208 | 8.37e-05 | 7.91e-05 |
| `(1,1024,24,128)` | 0.888 | 6.09e-05 | 6.06e-05 |
| `(1,2048,24,128)` | 3.627 | 4.43e-05 | 4.41e-05 |

### 5090 Z-Image server benchmark

Command shape: `zimage_image_t2i`, `1024x1024`, 9 denoise steps, `SGLANG_GEN_BASELINE=1`, `SGLANG_SKIP_CONSISTENCY=1`.

| backend | e2e ms | avg denoise ms | median denoise ms | transformer backend selected |
|---|---:|---:|---:|---|
| `torch_sdpa` | 2512.72 | 245.10 | 271.67 | `torch_sdpa` |
| `sm120_triton_attn` | 2709.41 | 267.21 | 295.55 | `sm120_triton_attn` |

Image-level comparison between the two generated JPG outputs with identical prompt/seed: SSIM `0.9475`, PSNR `25.87`, mean absolute pixel diff `3.54`.

Conclusion from the 5090 measurements: this implementation is numerically close to Torch SDPA at the attention-output level, but it is slower than Torch SDPA across the tested dense-attention shapes and also slower in the Z-Image end-to-end server case.

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28493301151](https://github.com/sgl-project/sglang/actions/runs/28493301151)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28493301074](https://github.com/sgl-project/sglang/actions/runs/28493301074)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
