---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] Fuse Wan VAE RMSNorm SiLU'
canonical_url: https://github.com/sgl-project/sglang/pull/30171
captured_at: '2026-07-07T23:35:30.913979+00:00'
content_hash: 66cb46d21f7f93d2178ebccdc7976e1062acc5dc7b3f6b328a57ee88422fe1fd
---
# [diffusion] Fuse Wan VAE RMSNorm SiLU

URL: https://github.com/sgl-project/sglang/pull/30171
State: closed
Labels: run-ci, diffusion, jit-kernel, run-ci-extra
Closed at: 2026-07-07T08:16:33Z
Merged at: 

## Motivation

Fuse the Wan VAE `RMSNorm -> SiLU` pattern used by FastWan2.2 TI2V decode. Decode dominates the FastWan preset, and this pattern appears repeatedly in the channel-first 5D VAE residual blocks and output head.

## Modifications

- Add a lightweight Triton `Wan VAE RMSNorm+SiLU` kernel for channel-first 5D tensors in `channels_last_3d` layout.
- Add a Python wrapper that preserves the original fallback path for grad mode, unsupported dtype/layout, non-CUDA tensors, unsupported channel counts, and runtime failures.
- Route Wan VAE residual blocks through the fused helper for `norm1 -> SiLU` and `norm2 -> SiLU`.
- Route encoder/decoder output heads through the fused helper for `norm_out -> SiLU`.
- Preserve output strides with `torch.empty_strided(x.shape, x.stride())` so the VAE keeps the `channels_last_3d` layout.
- Match eager op boundaries more closely: `F.normalize(x)`, `* scale`, `* gamma`, and `+ bias` each materialize in the output dtype before SiLU runs in fp32 and stores back to the output dtype.

## Accuracy Tests

Local syntax/format/lint checks passed before the final eager-boundary cast update:

```bash
python3 -m py_compile \
  python/sglang/multimodal_gen/runtime/models/vaes/wanvae.py \
  python/sglang/jit_kernel/diffusion/wan_rmsnorm_silu.py \
  python/sglang/jit_kernel/diffusion/triton/wan_rmsnorm_silu.py \
  test/registered/jit/diffusion/test_wan_rmsnorm_silu.py \
  test/registered/jit/benchmark/diffusion/bench_wan_rmsnorm_silu.py
python3 -m ruff format --check ...
python3 -m ruff check ...
git diff --check
```

H200 unit test on the final commit `65908633c2c8b85fc61a7bedd192390901252bcc`:

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=/tmp/sglang_local_validate/python \
  pytest -q test/registered/jit/diffusion/test_wan_rmsnorm_silu.py
```

Result: `13 passed`.

H200 FastWan consistency test on the final commit:

```bash
CUDA_VISIBLE_DEVICES=0 \
PYTHONPATH=/tmp/sglang_local_validate/python \
SGLANG_DIFFUSION_CONSISTENCY_PLATFORM=h100 \
SGLANG_DIFFUSION_ARTIFACT_DIR=/tmp/fastwan_candidate_artifacts \
pytest -s \
  python/sglang/multimodal_gen/test/server/test_server_1_gpu.py::TestDiffusionServerOneGpu::test_diffusion_generation[fastwan2_2_ti2v_5b] \
  --tb=short --disable-warnings
```

Result: `1 passed`.

| Metric | Value |
| --- | ---: |
| Min similarity | 0.9935 |
| Min SSIM | 0.9625 |
| Min PSNR | 39.8965 |
| Max mean_abs_diff | 1.6696 |
| SSIM threshold | 0.9200 |
| SSIM margin | +0.0425 |

Frame details:

| Frame | CLIP | SSIM | PSNR | mean_abs_diff |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 0.9970 | 0.9784 | 42.2418 | 1.0549 |
| 1 | 0.9979 | 0.9675 | 40.6121 | 1.4904 |
| 2 | 0.9935 | 0.9625 | 39.8965 | 1.6696 |

## Kernel Exactness Notes

A fully bitwise Triton replacement for the whole expression is not realistic here because ATen `F.normalize` maps to `x / torch.linalg.vector_norm(x)` and uses a different CUDA reduction path from the Triton row reduction; Triton and ATen SiLU also differ at the last-bit level. The final kernel therefore follows the closest practical contract: preserve the eager dtype materialization boundaries inside `WanRMS_norm.forward` while keeping the operation fused.

On random channel-first 5D H200 probes, the eager-boundary cast variant reduced bf16 mean absolute error versus the earlier fp32-affine fused version from roughly `0.0014-0.0016` to `0.0009-0.0011`, and the FastWan CI-GT `Min SSIM` improved from the earlier rerun's `0.921896` to `0.9625`.

## Speed Tests

H200 microbenchmark on the final commit:

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=/tmp/sglang_local_validate/python \
  python test/registered/jit/benchmark/diffusion/bench_wan_rmsnorm_silu.py
```

| Workload | Native us | Triton us | Speedup |
| --- | ---: | ---: | ---: |
| fastwan_decode_c384_t21_90x160 | 919.31 | 294.00 | 3.127x |
| fastwan_decode_c192_t41_180x320 | 3763.30 | 2098.53 | 1.793x |
| fastwan_decode_c96_t81_360x640 | 19973.03 | 13988.67 | 1.428x |

## FastWan End-to-End A/B

Same prompt, same seed, native SGLang backend, H200, `1280x720`, 81 frames. Both runs used:

```bash
CUDA_VISIBLE_DEVICES=0 FLASHINFER_DISABLE_VERSION_CHECK=1 PYTHONPATH=python \
python python/sglang/multimodal_gen/.claude/skills/sglang-diffusion-benchmark-profile/scripts/bench_diffusion_denoise.py \
  --model fastwan22-ti2v-5b \
  --label <baseline_steady|head_steady> \
  --output-dir /tmp/fastwan_bench_outputs
```

The helper command expands to:

```bash
sglang generate \
  --backend=sglang \
  --model-path=FastVideo/FastWan2.2-TI2V-5B-FullAttn-Diffusers \
  --prompt="The cat starts walking slowly towards the camera." \
  --seed=42 \
  --image-path=inputs/diffusion_benchmark/figs/cat.png \
  --width=1280 --height=720 --num-frames=81 \
  --save-output --warmup --enable-torch-compile \
  --perf-dump-path <perf.json>
```

Native backend gate passed: the logs used `backend: "sglang"` and `WanDMDPipeline`; no `Falling back to diffusers backend`, `Using diffusers backend`, or `Loaded diffusers pipeline` message appeared.

The first head run after clearing compile cache hit formal-shape compile during decode, so the table below reports the second steady run after the compile cache was populated for both baseline and head.

| Implementation | Commit | E2E | Denoising | Decoding | Peak memory | E2E delta | Decode delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | `3ea875fef48f6f01fa3bddd9e2197ad190cef29d` | 12246.18 ms | 950.58 ms | 10905.34 ms | 41.4 GB | - | - |
| Fused RMSNorm+SiLU | `65908633c2c8b85fc61a7bedd192390901252bcc` | 11749.78 ms | 951.72 ms | 10406.34 ms | 41.4 GB | -4.1% | -4.6% |

`compare_perf.py` stage breakdown:

| Stage Name | Baseline ms | New ms | Diff ms | Diff % |
| --- | ---: | ---: | ---: | ---: |
| InputValidationStage | 57.73 | 58.49 | +0.76 | +1.3% |
| TextEncodingStage | 327.82 | 328.04 | +0.22 | +0.1% |
| TimestepPreparationStage | 0.46 | 0.44 | -0.02 | -4.2% |
| LatentPreparationStage | 0.16 | 0.18 | +0.02 | +10.9% |
| DmdDenoisingStage | 950.58 | 951.72 | +1.14 | +0.1% |
| DecodingStage | 10905.34 | 10406.34 | -499.00 | -4.6% |

Same-prompt baseline-vs-fused video metrics across all 81 decoded frames:

| Metric | Value |
| --- | ---: |
| Frame count | 81 |
| Mean SSIM | 0.966360 |
| Min SSIM | 0.956900, frame 71 |
| Mean PSNR | 39.6679 |
| Min PSNR | 37.5693, frame 70 |
| Mean mean_abs_diff | 1.708694 |
| Max mean_abs_diff | 2.145390, frame 70 |
| Max abs diff | 84, frame 53 |

Representative frame metrics:

| Frame | SSIM | PSNR | mean_abs_diff | max_abs_diff |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 0.980479 | 43.1495 | 1.047048 | 28 |
| 40 | 0.966448 | 39.3046 | 1.735719 | 64 |
| 80 | 0.963899 | 39.0464 | 1.873097 | 49 |

## Result Video Frame Comparison

Same-prompt FastWan2.2 TI2V A/B output sample (`seed=42`, `1280x720`, 81 frames). Latest steady A/B numeric metrics are reported above; the image is kept as a visual reference for reviewer inspection.

![fastwan_compare_current.png](https://github.com/user-attachments/assets/2b1a40b9-1a59-4f19-b571-13a44d385553)

## Checklist

- [x] Default Wan VAE path tries the fused Triton helper first and falls back to the existing PyTorch implementation when unsupported.
- [x] Output strides/layout are preserved for `channels_last_3d` tensors.
- [x] H200 correctness test included.
- [x] H200 FastWan consistency test included.
- [x] H200 microbenchmark evidence included.
- [x] H200 FastWan end-to-end A/B evidence included.
- [x] Same-prompt generated-video frame comparison included.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28768288693](https://github.com/sgl-project/sglang/actions/runs/28768288693)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28768429826](https://github.com/sgl-project/sglang/actions/runs/28768429826)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
