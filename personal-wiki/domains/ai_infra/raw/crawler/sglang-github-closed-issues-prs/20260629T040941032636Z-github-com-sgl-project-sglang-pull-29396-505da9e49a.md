---
source_id: sglang-github-closed-issues-prs
title: '[Diffusion] Fuse LTX2 RMS AdaLN modulation'
canonical_url: https://github.com/sgl-project/sglang/pull/29396
captured_at: '2026-06-29T04:09:41.032636+00:00'
content_hash: 505da9e49a5660e9b94007744e744004e99f21f6f8516a6fee82e3f8c34bb7ac
---
# [Diffusion] Fuse LTX2 RMS AdaLN modulation

URL: https://github.com/sgl-project/sglang/pull/29396
State: closed
Labels: run-ci, diffusion, run-ci-extra
Closed at: 2026-06-28T11:22:46Z
Merged at: 

## Motivation

Fuse the repeated LTX-2.3 RMSNorm + AdaLN modulation pattern:

```python
norm_hidden_states = rms_norm(hidden_states) * (1 + scale) + shift
```

The LTX-2.3 HQ transformer hits this pattern in video/audio self-attention, prompt cross-attention, and MLP preparation. This PR follows the same LTX2 RMS AdaLN fusion opportunity used by NVlabs/Sana `sol-engine` at commit `00cb59836c297bd5fad401000ee65f9042f29d02`.

Unlike Sana's local Triton `ltx2_rms_norm_modulate` kernel, SGLang main already has a generic CUDA/CuTe DSL `sglang::fused_norm_scale_shift` primitive with RMSNorm and `[B, 1, D]` scale/shift broadcast support. This PR wires LTX2 into that existing primitive instead of adding another model-local kernel.

## Modifications

- Add a default-on LTX2 fused RMS AdaLN helper around `fused_norm_scale_shift(..., norm_type="rms")`.
- Keep no user-facing environment variable; unsupported shapes/devices/dtypes fall back to the original PyTorch expression.
- Disable the fused path for the current process after a runtime launch failure, then continue with the original path.
- Use the fused helper for LTX2 video/audio self-attention, prompt cross-attention, and MLP RMS AdaLN sites.
- Leave A2V/V2A dual modulation untouched, since that belongs to the separate dual-modulate fusion.
- Add a focused CUDA unit test for LTX2 broadcast scale/shift RMS AdaLN plus unsupported-hidden-size fallback.

## Accuracy Tests

Local:

```bash
python3 -m py_compile \
  python/sglang/multimodal_gen/runtime/models/dits/ltx_2.py \
  test/registered/jit/diffusion/test_ltx2_rms_adaln.py
python3 -m ruff format --check \
  python/sglang/multimodal_gen/runtime/models/dits/ltx_2.py \
  test/registered/jit/diffusion/test_ltx2_rms_adaln.py
python3 -m ruff check \
  python/sglang/multimodal_gen/runtime/models/dits/ltx_2.py \
  test/registered/jit/diffusion/test_ltx2_rms_adaln.py
git diff --check
```

B200:

```bash
CUDA_VISIBLE_DEVICES=7 \
PYTHONPATH=/tmp/sglang_rms_adaln_validate/python:/tmp/sglang_rms_adaln_validate \
FLASHINFER_DISABLE_VERSION_CHECK=1 \
pytest -q test/registered/jit/diffusion/test_ltx2_rms_adaln.py -s
```

Result: `3 passed`.

## Speed Tests

Command for both `main` and this PR:

```bash
CUDA_VISIBLE_DEVICES=7 \
PYTHONPATH=/tmp/sglang_rms_adaln_<impl>/python:/tmp/sglang_rms_adaln_<impl> \
FLASHINFER_DISABLE_VERSION_CHECK=1 \
HF_HUB_OFFLINE=1 \
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
sglang generate \
  --backend=sglang \
  --model-path=Lightricks/LTX-2.3 \
  --pipeline-class-name=LTX2TwoStageHQPipeline \
  --ltx2-two-stage-device-mode original \
  --prompt="A beautiful sunset over the ocean" \
  --seed=42 \
  --width=1920 --height=1088 --num-frames=121 \
  --num-inference-steps=15 \
  --save-output --warmup \
  --perf-dump-path /tmp/ltx23_rms_adaln_e2e/<impl>/perf.json \
  --output-file-path /tmp/ltx23_rms_adaln_e2e/<impl>/<impl>.mp4
```

- Host: `ion-b200`, NVIDIA B200, `CUDA_VISIBLE_DEVICES=7`.
- Model path: `Lightricks/LTX-2.3`, native `LTX2TwoStageHQPipeline`.
- Shape: T2V `1920x1088x121f`, HQ `num_inference_steps=15`, `seed=42`.
- Measurement: `sglang generate --warmup`; metric is `perf.json` `total_duration_ms`, with the warmup request excluded.
- Backend check: no diffusers fallback and no fused RMS AdaLN runtime-disable message observed in either run.

| Implementation | Commit | E2E ms | LTX2AVDenoisingStage ms | LTX2RefinementStage ms | LTX2AVDecodingStage ms | Peak reserved MB | Speedup |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Main | `a10a24e9a7` | 47389.96 | 29980.06 | 12770.02 | 4186.96 | 67902 | 1.00x |
| Fused RMS AdaLN | `8e8c1ccc06` | 46261.16 | 29442.09 | 12663.09 | 3711.15 | 67902 | 1.024x (+2.4%) |

Full perf artifacts: [main_perf.json](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-rms-adaln-assets/ltx2-rms-adaln/main_perf.json), [rms_adaln_perf.json](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-rms-adaln-assets/ltx2-rms-adaln/rms_adaln_perf.json), [compare_perf.md](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-rms-adaln-assets/ltx2-rms-adaln/compare_perf.md), [backend_check.log](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-rms-adaln-assets/ltx2-rms-adaln/backend_check.log).

## B200 Visual Output Check

Visual comparison uses the same full LTX-2.3 HQ command as the model benchmark above.

- Main commit: `a10a24e9a7`
- PR commit: `8e8c1ccc06`
- Prompt/shape: `A beautiful sunset over the ocean`, `1920x1088x121f`, `num_inference_steps=15`, `seed=42`
- Native `LTX2TwoStageHQPipeline` was used for both runs; no diffusers fallback was observed.
- FFmpeg decoded-video metrics over 121 frames: SSIM All `0.975513`, PSNR average `37.268533 dB`.

Left is `main`; right is this PR:

![LTX-2.3 HQ main vs fused RMS AdaLN visual comparison](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-rms-adaln-assets/ltx2-rms-adaln/main_vs_rms_adaln.gif)

MP4 artifacts: [main.mp4](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-rms-adaln-assets/ltx2-rms-adaln/main.mp4), [rms_adaln.mp4](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-rms-adaln-assets/ltx2-rms-adaln/rms_adaln.mp4), [side-by-side.mp4](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-rms-adaln-assets/ltx2-rms-adaln/main_vs_rms_adaln.mp4).

Metric logs: [ssim.log](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-rms-adaln-assets/ltx2-rms-adaln/ssim.log), [psnr.log](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-rms-adaln-assets/ltx2-rms-adaln/psnr.log).

## Checklist

- [x] Default path tries fused RMS AdaLN and falls back to the original expression when unsupported.
- [x] No environment variable is required to enable the fast path.
- [x] No A2V/V2A dual-modulation logic is changed in this PR.
- [x] CUDA unit test covers broadcast `[B, 1, D]` scale/shift and fallback.
- [x] B200 LTX-2.3 HQ native model benchmark completed.
- [x] B200 visual output comparison completed.





































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28316557666](https://github.com/sgl-project/sglang/actions/runs/28316557666)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28316557621](https://github.com/sgl-project/sglang/actions/runs/28316557621)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
