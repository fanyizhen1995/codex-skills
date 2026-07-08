---
source_id: sglang-github-closed-issues-prs
title: '[Diffusion] Add LTX2 TE NVFP4 FFN fast path'
canonical_url: https://github.com/sgl-project/sglang/pull/29315
captured_at: '2026-07-06T02:14:53.061506+00:00'
content_hash: 828a6de002159a2d6038333e17790f256d5995c043f8284f04f1c08c71a930b0
---
# [Diffusion] Add LTX2 TE NVFP4 FFN fast path

URL: https://github.com/sgl-project/sglang/pull/29315
State: closed
Labels: run-ci, diffusion, jit-kernel, run-ci-extra
Closed at: 2026-07-05T11:13:05Z
Merged at: 

## Motivation

This PR adds a reusable, opt-in runtime TE NVFP4 Linear/GEMM policy for experimenting with TransformerEngine NVFP4 on Blackwell. LTX2 video FFN, Wan2.2-T2V-A14B video FFN, and MOVA-720p video FFN are enabled targets, while TE import, module caching, fallback handling, bool opt-in gating, padding, and inference weight-workspace caching live in a generic runtime-layer helper that other model families can reuse selectively.

The path is disabled by default. It can be enabled with the boolean environment variable:

```bash
SGLANG_DIFFUSION_ENABLE_TE_NVFP4_LINEAR=1
```

If TransformerEngine is unavailable, the env var is disabled, the shape is not one of the explicitly wired video FFN shapes, TP is not 1, the weights are already quantized, or a runtime error is hit, the model falls back to the existing bf16/fp16 implementation.

Acknowledgement: this is motivated by the LTX2 FP4 / TE experimentation in NVLabs Sana `sol-engine`:

- https://github.com/NVlabs/Sana/tree/sol-engine
- https://github.com/NVlabs/Sana/blob/00cb59836c297bd5fad401000ee65f9042f29d02/python/sglang/multimodal_gen/runtime/models/dits/ltx_2.py

This PR keeps only the linear-only SGLang integration surface. It does not bring over the broader Sana fullopt stack such as KWL elementwise fusions, stage-1 cache, sparse attention, or token pruning.

## Modifications

- Add a reusable runtime TE NVFP4 Linear runner in `runtime/layers/low_precision_linear.py`.
- Add bool opt-in selection with `SGLANG_DIFFUSION_ENABLE_TE_NVFP4_LINEAR`.
- Thread an optional TE NVFP4 target through the shared multimodal `MLP` layer.
- Wire the LTX2 video FFN shape `4096 -> 16384 -> 4096` and the Wan/MOVA video FFN shape `5120 -> 13824 -> 5120` to the new helper, and only pass those targets when `SGLANG_DIFFUSION_ENABLE_TE_NVFP4_LINEAR` is true.
- Reuse the loaded SGLang linear weights inside cached TE `Linear` modules for `proj_in` and `proj_out`.
- Cache TE quantized weight workspaces during inference by passing `is_first_microbatch=True` on the first successful call for each cached TE `Linear`, then `False` on later calls.
- Reset the weight-cache readiness state when the source weight or bias object changes.
- Keep training mode on TE's default path by passing `is_first_microbatch=None`.
- Keep audio FFN, unsupported video FFN shapes, and default execution unchanged.
- Keep the TE recipe fixed to the validated conservative settings:
  - `disable_rht=True`
  - `disable_stochastic_rounding=True`
  - `disable_2d_quantization=True`
- Keep M padding fixed to the validated value `16` instead of exposing it as another runtime knob.
- Add unit coverage for default-disabled bool policy, true/false env parsing, Wan/MOVA target shape gating, shared MLP TE dispatch, CPU fallback short-circuiting, inference weight-cache reuse, weight-object cache reset, and training-mode no-cache behavior.
- Remove the earlier fused GELU / fused residual-gate experiments from this PR after B200 validation showed they regress the real LTX-2.3 path.

## Accuracy / Static Checks

Local checks:

```bash
python3 -m ruff format --check \
  python/sglang/multimodal_gen/runtime/layers/low_precision_linear.py \
  python/sglang/multimodal_gen/runtime/layers/mlp.py \
  python/sglang/multimodal_gen/runtime/models/dits/wanvideo.py \
  python/sglang/multimodal_gen/runtime/models/dits/mova_video_dit.py \
  python/sglang/multimodal_gen/test/unit/test_low_precision_linear.py
python3 -m ruff check \
  python/sglang/multimodal_gen/runtime/layers/low_precision_linear.py \
  python/sglang/multimodal_gen/runtime/layers/mlp.py \
  python/sglang/multimodal_gen/runtime/models/dits/wanvideo.py \
  python/sglang/multimodal_gen/runtime/models/dits/mova_video_dit.py \
  python/sglang/multimodal_gen/test/unit/test_low_precision_linear.py
python3 -m compileall -q \
  python/sglang/multimodal_gen/runtime/layers/low_precision_linear.py \
  python/sglang/multimodal_gen/runtime/layers/mlp.py \
  python/sglang/multimodal_gen/runtime/models/dits/wanvideo.py \
  python/sglang/multimodal_gen/runtime/models/dits/mova_video_dit.py \
  python/sglang/multimodal_gen/test/unit/test_low_precision_linear.py
git diff --check
```

Result:

```text
5 files already formatted
All checks passed!
```

B200 unit test on `cirrascale-gpuc523`, container `sglang_bbuf_pr29315_wc`, image `radixark/miles:dev`:

```bash
PYTHONPATH=python python3 python/sglang/multimodal_gen/test/unit/test_low_precision_linear.py
```

Result:

```text
Ran 9 tests in 0.006s
OK
```

B200 module smoke with actual TransformerEngine on `cirrascale-gpuc523` (`torch 2.11.0+cu129`, TransformerEngine 2.10.0):

```text
y1_finite True
y2_finite True
cache_ready ['linear']
workspace_keys_after_first ['weight']
workspace_keys_after_second ['weight']
weight_workspace_type NVFP4Tensor
same_shape (17, 128) (17, 128)
```

The updated unit test and actual-TE MLP smoke also passed on `ion-b200` (`torch 2.11.0+cu130`, TransformerEngine 2.12.0):

```text
Ran 12 tests in 0.005s
OK

finite True True
shape (3, 17, 128) (3, 17, 128)
runner TeNvfp4LinearRunner
cache_keys ['fc_in', 'fc_out']
weight_cache_ready ['fc_in', 'fc_out']
```

## End-to-End Benchmark

Host and software:

- Host: `cirrascale-gpuc523`
- GPU: NVIDIA B200, `CUDA_VISIBLE_DEVICES=4`
- Container: `sglang_bbuf_pr29315_wc`
- Image: `radixark/miles:dev`
- Torch: `2.11.0+cu129`
- TransformerEngine: `2.10.0`
- SGLang commit: `fdcea9dd5cb1deb40b3796a011e509744120391a`

Both runs used native SGLang diffusion:

```text
✓ Using explicitly specified pipeline: LTX2Pipeline (class: LTX2Pipeline)
```

No `Falling back to diffusers backend`, `Using diffusers backend`, `Loaded diffusers pipeline`, or `Disabling LTX2 TE NVFP4` message was observed.

Baseline command:

```bash
CUDA_VISIBLE_DEVICES=4 \
PYTHONPATH=python \
FLASHINFER_DISABLE_VERSION_CHECK=1 \
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
sglang generate \
  --backend=sglang \
  --model-path=Lightricks/LTX-2.3 \
  --pipeline-class-name=LTX2Pipeline \
  --prompt="a small robot writing code on a desk" \
  --negative-prompt="shaky, glitchy, low quality, worst quality, deformed, distorted, disfigured, motion smear, motion artifacts, fused fingers, bad anatomy, weird hand, ugly, transition, static." \
  --height=512 --width=768 --num-frames=121 --fps=24 \
  --num-inference-steps=30 --guidance-scale=3.0 --seed=1234 \
  --warmup --save-output \
  --component-attention-backends text_encoder=torch_sdpa \
  --perf-dump-path /tmp/ltx23_te_nvfp4_weight_cache_e2e/baseline/perf.json \
  --output-file-path /tmp/ltx23_te_nvfp4_weight_cache_e2e/baseline/baseline.mp4
```

TE NVFP4 command, shown with the current bool env name after this follow-up change:

```bash
CUDA_VISIBLE_DEVICES=4 \
PYTHONPATH=python \
FLASHINFER_DISABLE_VERSION_CHECK=1 \
HF_HUB_OFFLINE=1 \
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
SGLANG_DIFFUSION_ENABLE_TE_NVFP4_LINEAR=1 \
sglang generate \
  --backend=sglang \
  --model-path=Lightricks/LTX-2.3 \
  --pipeline-class-name=LTX2Pipeline \
  --prompt="a small robot writing code on a desk" \
  --negative-prompt="shaky, glitchy, low quality, worst quality, deformed, distorted, disfigured, motion smear, motion artifacts, fused fingers, bad anatomy, weird hand, ugly, transition, static." \
  --height=512 --width=768 --num-frames=121 --fps=24 \
  --num-inference-steps=30 --guidance-scale=3.0 --seed=1234 \
  --warmup --save-output \
  --component-attention-backends text_encoder=torch_sdpa \
  --perf-dump-path /tmp/ltx23_te_nvfp4_weight_cache_e2e/te/perf.json \
  --output-file-path /tmp/ltx23_te_nvfp4_weight_cache_e2e/te/te_nvfp4_weight_cache.mp4
```

Results, with the warmup request excluded:

| Variant | Frames | Steps | E2E request ms | Denoise stage ms | Denoise ms / step | Peak reserved MB | Speedup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline bf16/fp16 FFN | 121 | 30 | 32317.33 | 30949.92 | 1031.5 | 53398 | 1.00x |
| TE NVFP4 FFN, cached weights | 121 | 30 | 26282.13 | 25000.99 | 833.2 | 57238 | **1.230x E2E / 1.238x denoise** |

`compare_perf.py` summary:

```text
E2E Latency: 32317.33 ms -> 26282.13 ms, -6035.20 ms (-18.7%)
LTX2AVDenoisingStage: 30949.92 ms -> 25000.99 ms, -5948.93 ms (-19.2%)
```

The cached TE weight workspace is expected to increase peak reserved memory. In this run peak reserved memory went from `53398 MB` to `57238 MB` (`+3840 MB`) while avoiding repeated runtime weight quantization.

Perf artifacts:

- Baseline perf JSON: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-weight-cache/baseline_perf.json
- TE NVFP4 weight-cache perf JSON: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-weight-cache/te_nvfp4_weight_cache_perf.json
- Baseline run log: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-weight-cache/baseline_run.log
- TE NVFP4 weight-cache run log: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-weight-cache/te_nvfp4_weight_cache_run.log


## Follow-up Bool Env Video Benchmarks

This follow-up was collected after changing the opt-in to `SGLANG_DIFFUSION_ENABLE_TE_NVFP4_LINEAR=1` and wiring the Wan/MOVA video FFNs into the shared TE NVFP4 `MLP` path.

Host and software:

- Host: `ion-b200`
- GPU: NVIDIA B200; single GPU for LTX-2.3 and MOVA-720p, 4 GPUs (`CUDA_VISIBLE_DEVICES=0,1,2,7`) for Wan2.2-T2V-A14B
- Container: `sglang_bbuf_pr29315`
- Image: `radixark/miles:dev`
- Torch: `2.11.0+cu130`
- TransformerEngine: `2.12.0`
- SGLang code snapshot: PR head `37dc11e3ff`

All runs used native SGLang diffusion. No `Falling back to diffusers backend`, `Using diffusers backend`, `Loaded diffusers pipeline`, or `Disabling TE NVFP4` message was observed. The Wan and MOVA TE runs also logged the actual model hooks:

```text
Using TE NVFP4 linear runtime path for wan.video_ffn
Using TE NVFP4 linear runtime path for mova.video_ffn
```

Results, with the warmup request excluded:

| Model | Variant | Frames | Steps | E2E request ms | Denoise stage ms | Denoise ms / step | Peak reserved MB | Speedup |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| LTX-2.3 | Baseline bf16/fp16 FFN | 121 | 30 | 30273.76 | 28708.79 | 957.0 | 53398 | 1.000x |
| LTX-2.3 | TE NVFP4 FFN, bool env | 121 | 30 | 33226.05 | 31363.06 | 1045.4 | 57238 | 0.911x E2E / 0.915x denoise |
| Wan2.2-T2V-A14B | Baseline | 81 | 40 | 136487.53 | 132936.63 | 3323.4 | 12898 | 1.000x |
| Wan2.2-T2V-A14B | TE NVFP4 video FFN | 81 | 40 | 129978.72 | 125925.79 | 3148.1 | 19250 | 1.050x E2E / 1.056x denoise |
| MOVA-720p | Baseline | 193 | 2 | 129795.81 | 116566.47 | 58283.2 | 74980 | 1.000x |
| MOVA-720p | TE NVFP4 video FFN | 193 | 2 | 117990.22 | 104741.60 | 52370.8 | 80040 | 1.100x E2E / 1.113x denoise |

`compare_perf.py` summaries:

```text
LTX-2.3: E2E 30273.76 ms -> 33226.05 ms, +2952.29 ms (+9.8%); LTX2AVDenoisingStage 28708.79 ms -> 31363.06 ms, +2654.26 ms (+9.2%)
Wan2.2-T2V-A14B: E2E 136487.53 ms -> 129978.72 ms, -6508.82 ms (-4.8%); DenoisingStage 132936.63 ms -> 125925.79 ms, -7010.84 ms (-5.3%)
MOVA-720p: E2E 129795.81 ms -> 117990.22 ms, -11805.59 ms (-9.1%); MOVADenoisingStage 116566.47 ms -> 104741.60 ms, -11824.87 ms (-10.1%)
```

On `ion-b200` with TransformerEngine 2.12.0, the LTX-2.3 bool-env run was slower than baseline, unlike the primary TransformerEngine 2.10.0 result above. The run still verifies that the bool env enters the TE path: peak reserved memory increased from `53398 MB` to `57238 MB`, matching the cached TE workspace behavior. For Wan and MOVA, the new measurements are actual hooked TE runs, not merely bool-env-on variance.

Additional perf artifacts:

- LTX-2.3 baseline perf JSON: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-bool-env-ion-b200/ltx23_baseline/perf.json
- LTX-2.3 bool-env perf JSON: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-bool-env-ion-b200/ltx23_te/perf.json
- LTX-2.3 baseline run log: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-bool-env-ion-b200/ltx23_baseline/run.log
- LTX-2.3 bool-env run log: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-bool-env-ion-b200/ltx23_te/run.log
- Wan2.2-T2V-A14B baseline perf JSON: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-wan-mova-hook-ion-b200/wan_t2v_a14b_baseline/wan-t2v_baseline_hook.json
- Wan2.2-T2V-A14B TE NVFP4 perf JSON: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-wan-mova-hook-ion-b200/wan_t2v_a14b_te/wan-t2v_te_hook.json
- Wan2.2-T2V-A14B baseline run log: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-wan-mova-hook-ion-b200/wan_t2v_a14b_baseline/run.log
- Wan2.2-T2V-A14B TE NVFP4 run log: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-wan-mova-hook-ion-b200/wan_t2v_a14b_te/run.log
- Wan2.2-T2V-A14B compare output: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-wan-mova-hook-ion-b200/wan_t2v_a14b_compare.txt
- MOVA-720p baseline perf JSON: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-wan-mova-hook-ion-b200/mova_720p_1gpu_baseline/mova-720p_baseline_hook.json
- MOVA-720p TE NVFP4 perf JSON: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-wan-mova-hook-ion-b200/mova_720p_1gpu_te/mova-720p_te_hook.json
- MOVA-720p baseline run log: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-wan-mova-hook-ion-b200/mova_720p_1gpu_baseline/run.log
- MOVA-720p TE NVFP4 run log: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-wan-mova-hook-ion-b200/mova_720p_1gpu_te/run.log
- MOVA-720p compare output: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-wan-mova-hook-ion-b200/mova_720p_1gpu_compare.txt

## Visual Output Check

This is a lossy FP4 runtime path, so exact visual parity is not expected. The check below compares the same prompt, seed, shape, frame count, and 30-step sampling setup as the benchmark above.

- SSIM All: `0.675794`
- PSNR average: `18.486353 dB`

Left is baseline bf16/fp16 FFN; right is TE NVFP4 FFN with cached weights:

![LTX-2.3 baseline vs TE NVFP4 weight-cache comparison](https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-weight-cache/baseline_vs_te_weight_cache.gif)

MP4 artifacts:

- Baseline: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-weight-cache/baseline.mp4
- TE NVFP4 weight-cache: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-weight-cache/te_nvfp4_weight_cache.mp4
- Side-by-side: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-weight-cache/baseline_vs_te_weight_cache.mp4
- SSIM log: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-weight-cache/ssim.log
- PSNR log: https://raw.githubusercontent.com/BBuf/sglang/pr-ltx2-te-nvfp4-assets/ltx2-te-nvfp4-weight-cache/psnr.log

## Checklist

- [x] Runtime TE NVFP4 Linear helper is generic and bool-gated.
- [x] Default bool env is false, and LTX2 passes no TE NVFP4 target unless `SGLANG_DIFFUSION_ENABLE_TE_NVFP4_LINEAR` is true.
- [x] LTX2 video FFN can be enabled with `SGLANG_DIFFUSION_ENABLE_TE_NVFP4_LINEAR=1`.
- [x] TE import/runtime failure falls back to the existing bf16/fp16 FFN path.
- [x] TE weight workspace cache is built once per cached inference `Linear` and reused on later calls.
- [x] Cache state resets when the source weight/bias object changes and stays disabled in training mode.
- [x] Audio FFN is unchanged.
- [x] TP > 1, quantized weights, unsupported dtypes, LoRA-unmerged layers, and unsupported shapes do not enter the TE path.
- [x] B200 module smoke confirms TE creates an NVFP4 weight workspace.
- [x] Native LTX-2.3 one-stage 30-step benchmark completed.
- [x] Follow-up bool-env LTX-2.3 benchmark completed on B200.
- [x] Wan2.2-T2V-A14B and MOVA-720p video FFNs are wired to the TE NVFP4 path and benchmarked on B200.
- [x] Output video comparison and SSIM/PSNR check completed.

## Review and Merge Process

This PR is intentionally narrow. It adds the reusable runtime low-precision Linear policy requested in review and wires only explicit, experimental, opt-in video FFN targets for LTX2, Wan2.2-T2V-A14B, and MOVA-720p. Broader Sana-derived lossless fusions or additional model targets should be handled as separate PRs with their own ablation and end-to-end evidence.

























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28735232050](https://github.com/sgl-project/sglang/actions/runs/28735232050)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28735232005](https://github.com/sgl-project/sglang/actions/runs/28735232005)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
