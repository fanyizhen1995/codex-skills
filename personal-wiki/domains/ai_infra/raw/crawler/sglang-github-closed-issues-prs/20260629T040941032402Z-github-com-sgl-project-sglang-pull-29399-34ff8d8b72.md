---
source_id: sglang-github-closed-issues-prs
title: '[Diffusion] Fuse LTX2 qknorm split-RoPE'
canonical_url: https://github.com/sgl-project/sglang/pull/29399
captured_at: '2026-06-29T04:09:41.032402+00:00'
content_hash: 34ff8d8b723fdc0189528859e9fe04a7cb023c825b1f2c8aee8753f534ec4b12
---
# [Diffusion] Fuse LTX2 qknorm split-RoPE

URL: https://github.com/sgl-project/sglang/pull/29399
State: closed
Labels: run-ci, diffusion, jit-kernel, run-ci-extra
Closed at: 2026-06-28T11:22:49Z
Merged at: 

## Motivation

Fuse the LTX-2.3 attention Q/K RMSNorm + split-RoPE sequence into one Triton fast path.

This follows the optimization direction used by NVIDIA Sana's sol-engine branch:
[`NVlabs/Sana@00cb598`](https://github.com/NVlabs/Sana/tree/00cb59836c297bd5fad401000ee65f9042f29d02), specifically its LTX2 fused qknorm + split-RoPE path. This PR adapts the idea to SGLang's current native diffusion implementation and keeps SGLang's default guarded-fallback behavior.

The hot pattern in `LTX2Attention.forward` is:

```python
q = self.q_norm(q)
k = self.k_norm(k)
q = apply_split_rotary_emb(q, (cos, sin))
k = apply_split_rotary_emb(k, (k_cos, k_sin))
```

For LTX-2.3 HQ, this appears in both stage-1 denoising and stage-2 refinement, including large split-RoPE rows such as the stage-2 packed video latent shape `[1, 32640, 128]`.

## Modifications

- Add `sglang.jit_kernel.diffusion.triton.ltx2_qknorm.ltx2_qknorm_split_rope_pair`.
- Fuse Q and K RMSNorm with split-RoPE in a pair kernel for BF16 `[batch, seq, hidden]` tensors.
- Wire `LTX2Attention.forward` to try the fused path before the existing separate RMSNorm + split-RoPE path.
- Keep the path default-on but narrowly guarded:
  - TP world size must be 1.
  - `q_norm` / `k_norm` must be `torch.nn.RMSNorm`.
  - Q/K and split-RoPE tensors must be CUDA BF16 with the expected contiguous/4D split-RoPE layout.
  - Unsupported shapes or dtypes fall back to the existing implementation.
  - Runtime kernel failure disables this fast path for the process and logs a `warning_once`.
- Add CUDA correctness coverage for same-seq and different-seq Q/K shapes plus interleaved-RoPE fallback.

## Accuracy Tests

Local:

```bash
python3 -m py_compile \
  python/sglang/multimodal_gen/runtime/models/dits/ltx_2.py \
  python/sglang/jit_kernel/diffusion/triton/ltx2_qknorm.py \
  test/registered/jit/diffusion/test_ltx2_qknorm_split_rope.py
python3 -m ruff format --check \
  python/sglang/multimodal_gen/runtime/models/dits/ltx_2.py \
  python/sglang/jit_kernel/diffusion/triton/ltx2_qknorm.py \
  test/registered/jit/diffusion/test_ltx2_qknorm_split_rope.py
python3 -m ruff check \
  python/sglang/multimodal_gen/runtime/models/dits/ltx_2.py \
  python/sglang/jit_kernel/diffusion/triton/ltx2_qknorm.py \
  test/registered/jit/diffusion/test_ltx2_qknorm_split_rope.py
git diff --check
```

Result: all checks passed.

B200:

```bash
CUDA_VISIBLE_DEVICES=7 \
PYTHONPATH=/tmp/sglang_qknorm_split_rope_validate/python:/tmp/sglang_qknorm_split_rope_validate \
FLASHINFER_DISABLE_VERSION_CHECK=1 \
pytest -q test/registered/jit/diffusion/test_ltx2_qknorm_split_rope.py -s
```

Result: `3 passed, 20 warnings`.

## Speed Tests

B200 model E2E benchmark:

```bash
CUDA_VISIBLE_DEVICES=7 \
PYTHONPATH=/tmp/sglang_qknorm_split_rope_<impl>/python:/tmp/sglang_qknorm_split_rope_<impl> \
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
  --perf-dump-path /tmp/ltx23_qknorm_split_rope_e2e/<impl>/perf.json \
  --output-file-path /tmp/ltx23_qknorm_split_rope_e2e/<impl>/<impl>.mp4
```

- Host: `ion-b200`, NVIDIA B200, `CUDA_VISIBLE_DEVICES=7`.
- Main commit: `5996b54bd3`; PR commit: `4e94cb0792`.
- Model path: `Lightricks/LTX-2.3`, native `LTX2TwoStageHQPipeline`.
- Shape: T2V `1920x1088x121f`, recommended HQ `num_inference_steps=15`, `seed=42`.
- Measurement: `sglang generate --warmup`; metric is `perf.json` `total_duration_ms`, with the warmup request excluded.
- Backend gate: both logs show `Using explicitly specified pipeline: LTX2TwoStageHQPipeline`; no diffusers fallback was observed.
- Fast-path stability gate: no `Disabling LTX2 fused q/k norm + split-RoPE` warning was observed.

| Implementation | E2E ms | LTX2AVDenoisingStage ms | LTX2RefinementStage ms | LTX2AVDecodingStage ms | Peak reserved MB | Speedup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Main | 46737.57 | 29851.18 | 12749.93 | 3692.71 | 67902 | 1.000x |
| Fused qknorm + split-RoPE | 46316.99 | 29493.81 | 12661.86 | 3711.42 | 67902 | **1.009x (+0.91%)** |

## B200 Visual Output Check

Visual equivalence check uses the same full LTX-2.3 HQ command as the model benchmark above.

- Host/GPU: `ion-b200`, NVIDIA B200, `CUDA_VISIBLE_DEVICES=7`.
- Main commit: `5996b54bd3`; PR commit: `4e94cb0792`.
- Prompt/shape: `A beautiful sunset over the ocean`, `1920x1088x121f`, recommended HQ `num_inference_steps=15`, `seed=42`.
- Native `LTX2TwoStageHQPipeline` was used for both runs; no diffusers fallback was observed.
- Decoded-video comparison: SSIM All `0.984495`, PSNR average `39.982356 dB`.

Left is `main`; right is this PR:

![LTX-2.3 HQ main vs fused qknorm split-RoPE visual comparison](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-qknorm-split-rope-assets/ltx2-qknorm-split-rope/assets/main_vs_qknorm_split_rope.gif)

MP4 artifacts: [main.mp4](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-qknorm-split-rope-assets/ltx2-qknorm-split-rope/main/main.mp4), [pr.mp4](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-qknorm-split-rope-assets/ltx2-qknorm-split-rope/qknorm_split_rope/qknorm_split_rope.mp4), [side-by-side.mp4](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-qknorm-split-rope-assets/ltx2-qknorm-split-rope/assets/main_vs_qknorm_split_rope.mp4).

## Checklist

- [x] Sana sol-engine optimization source acknowledged.
- [x] Default path tries fused qknorm + split-RoPE and falls back safely.
- [x] No environment variable is required to enable the fast path.
- [x] B200 CUDA correctness test included.
- [x] B200 LTX-2.3 HQ native-backend E2E benchmark included.
- [x] Visual output comparison included.

















































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28317018035](https://github.com/sgl-project/sglang/actions/runs/28317018035)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28317017979](https://github.com/sgl-project/sglang/actions/runs/28317017979)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
