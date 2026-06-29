---
source_id: sglang-github-closed-issues-prs
title: '[Diffusion] Fuse LTX2 dual modulation'
canonical_url: https://github.com/sgl-project/sglang/pull/29392
captured_at: '2026-06-29T04:09:41.032903+00:00'
content_hash: b10f48f279d2c05fa1caf19c8e1223a1ce1ab32c3c1727e715028f44cef6444b
---
# [Diffusion] Fuse LTX2 dual modulation

URL: https://github.com/sgl-project/sglang/pull/29392
State: closed
Labels: run-ci, diffusion, jit-kernel, run-ci-extra
Closed at: 2026-06-28T11:22:43Z
Merged at: 

## Motivation

Fuse the LTX-2.3 audio/video cross-attention modulation path.

The original path computes RMSNorm once, then materializes two independently modulated tensors for A2V and V2A:

```python
norm = rms_norm(x)
a2v = norm * (1 + a2v_scale) + a2v_shift
v2a = norm * (1 + v2a_scale) + v2a_shift
```

For LTX-2.3 HQ shapes this runs on large video token rows such as `[1, 32640, 4096]`. The same normalized tensor feeds two scale/shift branches, so it is a good small fusion target.

This PR is adapted from the dual-modulation idea in [NVlabs/Sana `sol-engine`](https://github.com/NVlabs/Sana/tree/sol-engine), specifically [`ltx2_dual_modulate.py` from `NVlabs/Sana@00cb598`](https://github.com/NVlabs/Sana/blob/00cb59836c297bd5fad401000ee65f9042f29d02/python/sglang/jit_kernel/diffusion/triton/ltx2_dual_modulate.py). This PR only ports the `dual_modulate` / `ca_dual_modulate` slice and keeps it independent from the other Sana LTX2 fuse experiments.

## Modifications

- Add `ltx2_rmsnorm_dual_modulate`, which fuses RMSNorm plus two scale/shift modulations.
- Add `ltx2_rmsnorm_ca_dual_modulate_from_temb`, which also folds the LTX2 CA `scale_shift_table + temb` materialization into the same kernel.
- Wire the LTX2 A2V/V2A cross-attention modulation path to try CA dual-modulate first, then dual-modulate, then fall back to the original RMSNorm plus PyTorch scale/shift path.
- Keep the fast path enabled by default with no user-facing environment variable.
- Add B200 CUDA correctness coverage for both fused entry points.

## Accuracy Tests

Local static checks:

```bash
python3 -m ruff format --check \
  python/sglang/jit_kernel/diffusion/triton/ltx2_dual_modulate.py \
  python/sglang/multimodal_gen/runtime/models/dits/ltx_2.py \
  test/registered/jit/diffusion/test_ltx2_dual_modulate.py
python3 -m ruff check \
  python/sglang/jit_kernel/diffusion/triton/ltx2_dual_modulate.py \
  python/sglang/multimodal_gen/runtime/models/dits/ltx_2.py \
  test/registered/jit/diffusion/test_ltx2_dual_modulate.py
python3 -m py_compile \
  python/sglang/jit_kernel/diffusion/triton/ltx2_dual_modulate.py \
  python/sglang/multimodal_gen/runtime/models/dits/ltx_2.py \
  test/registered/jit/diffusion/test_ltx2_dual_modulate.py
git diff --check
```

B200 CUDA unit test:

```bash
CUDA_VISIBLE_DEVICES=7 \
PYTHONPATH=python \
FLASHINFER_DISABLE_VERSION_CHECK=1 \
pytest -q test/registered/jit/diffusion/test_ltx2_dual_modulate.py -s
```

Result: `8 passed, 1 skipped`.

## Speed Tests

B200 model E2E benchmark:

```bash
CUDA_VISIBLE_DEVICES=7 \
PYTHONPATH=/tmp/sglang_dual_modulate_<impl>/python:/tmp/sglang_dual_modulate_<impl> \
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
  --perf-dump-path /tmp/ltx23_dual_mod_e2e/<impl>/perf.json \
  --output-file-path /tmp/ltx23_dual_mod_e2e/<impl>/<impl>.mp4
```

- Host: `ion-b200`, NVIDIA B200, `CUDA_VISIBLE_DEVICES=7`.
- Baseline commit: `a10a24e9a7`.
- PR commit: `0eebf449eb`.
- Model path: `Lightricks/LTX-2.3`, native `LTX2TwoStageHQPipeline`; no diffusers fallback observed.
- Shape: T2V `1920x1088x121f`, HQ `num_inference_steps=15`, `seed=42`.
- Measurement: `sglang generate --warmup`; metric is `perf.json` `total_duration_ms`, with warmup excluded.

| Implementation | E2E ms | LTX2AVDenoisingStage ms | LTX2RefinementStage ms | Peak reserved MB | Speedup |
| --- | ---: | ---: | ---: | ---: | ---: |
| Main | 46856.69 | 29914.72 | 12773.60 | 67902 | 1.00x |
| Fused dual-modulate | 45764.31 | 28644.38 | 12412.10 | 68402 | **1.024x (+2.3%)** |

`compare_perf.py` reported:

```text
E2E Latency: 46856.69 ms -> 45764.31 ms, -1092.38 ms (-2.3%)
LTX2AVDenoisingStage: 29914.72 ms -> 28644.38 ms, -1270.33 ms (-4.2%)
LTX2RefinementStage: 12773.60 ms -> 12412.10 ms, -361.50 ms (-2.8%)
```

## B200 Visual Output Check

Visual comparison uses the same full LTX-2.3 HQ command as the model benchmark above.

- Decoded-video comparison: SSIM All `0.981823`, PSNR average `39.144663 dB`.
- This path changes the RMSNorm reduction order in BF16, so decoded frames are not bit-exact. The fusion is mathematically equivalent, and the output remains visually close to the main baseline.

Left is `main`; right is this PR:

![LTX-2.3 HQ main vs fused dual-modulate](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-dual-mod-assets/ltx2-dual-modulate/main_vs_dual.gif)

MP4 artifacts: [main.mp4](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-dual-mod-assets/ltx2-dual-modulate/main.mp4), [dual.mp4](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-dual-mod-assets/ltx2-dual-modulate/dual.mp4), [side-by-side.mp4](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-dual-mod-assets/ltx2-dual-modulate/main_vs_dual.mp4).

Perf and metric artifacts: [main_perf.json](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-dual-mod-assets/ltx2-dual-modulate/main_perf.json), [dual_perf.json](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-dual-mod-assets/ltx2-dual-modulate/dual_perf.json), [ssim.log](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-dual-mod-assets/ltx2-dual-modulate/ssim.log), [psnr.log](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-dual-mod-assets/ltx2-dual-modulate/psnr.log).

## Checklist

- [x] Default path tries CA dual-modulate, then dual-modulate, then falls back to the original path.
- [x] No environment variable is required to enable this optimization.
- [x] B200 CUDA correctness test passed.
- [x] LTX-2.3 HQ native model benchmark completed on B200.
- [x] Video output compared against `main`.

## Review and Merge Process

This is a focused Sana-inspired follow-up for the LTX2 A2V/V2A cross-attention modulation path. The whole-model speedup is modest but measurable on the LTX-2.3 HQ path, and most of the gain appears in the denoising stage where the fused cross-attention modulation is exercised repeatedly.

























































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28315930239](https://github.com/sgl-project/sglang/actions/runs/28315930239)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28315930137](https://github.com/sgl-project/sglang/actions/runs/28315930137)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
