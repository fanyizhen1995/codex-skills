---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] feat: enable compile warmup for vae decode'
canonical_url: https://github.com/sgl-project/sglang/pull/29306
captured_at: '2026-07-05T02:14:10.257473+00:00'
content_hash: 90975dbda04dc2712c566ee37655b84bb2a724ed47ccb7da3ff817a857e64cd4
---
# [diffusion] feat: enable compile warmup for vae decode

URL: https://github.com/sgl-project/sglang/pull/29306
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-04T07:25:27Z
Merged at: 2026-07-04T07:25:27Z

## Summary

This PR makes `--enable-torch-compile` cover the diffusion decode hot path without making the first live request pay compile latency.

Changes:
- compile VAE `decode` from `DecodingStage` when `--enable-torch-compile` is enabled
- use a VAE-specific default compile mode of `default`, with overrides via `SGLANG_VAE_TORCH_COMPILE_MODE` or `SGLANG_TORCH_COMPILE_MODE`
- automatically enable server warmup for torch compile when no warmup mode is explicitly configured
- preserve explicit `--warmup-steps` for torch-compile server warmup
- add internal non-warmup pretraffic requests before the server is marked ready, so the real request path is also compiled
- fix Z-Image caption conditioning so DiT receives bucket-padded caption tensors plus tensor valid lengths, avoiding per-prompt-length graph recompiles

## Why

VAE compile improves steady-state decode latency, but the first compiled VAE call can be very expensive. Separately, a normal warmup request was not enough for first live traffic because warmup and real requests can exercise different branches. Z-Image also exposed a prompt-length guard issue: caption embeddings were padded inside the compiled transformer forward, so different raw prompt lengths triggered new graphs even when they belonged to the same padded bucket.

## Validation

Remote validation on a non-CI 1x H100 rx devbox, base `origin/main` `bc150173b`.

Unit tests:

```bash
python3 -m pytest \
  python/sglang/multimodal_gen/test/unit/test_server_args.py::TestWarmupModeNormalization \
  python/sglang/multimodal_gen/test/unit/test_cfg_parallel_warmup.py::TestWarmupReqCfgParallel \
  -q
```

Result: `37 passed`.

Pre-commit:

```bash
pre-commit run --files \
  python/sglang/multimodal_gen/configs/pipeline_configs/zimage.py \
  python/sglang/multimodal_gen/runtime/managers/scheduler.py \
  python/sglang/multimodal_gen/runtime/models/dits/zimage.py \
  python/sglang/multimodal_gen/runtime/pipelines_core/stages/decoding.py \
  python/sglang/multimodal_gen/runtime/server_args.py \
  python/sglang/multimodal_gen/runtime/server_warmup.py \
  python/sglang/multimodal_gen/runtime/warmup_request_builder.py \
  python/sglang/multimodal_gen/test/unit/test_cfg_parallel_warmup.py \
  python/sglang/multimodal_gen/test/unit/test_server_args.py
```

Result: passed.

Server smoke:

```bash
sglang serve \
  --model-path Tongyi-MAI/Z-Image-Turbo \
  --host 127.0.0.1 \
  --port 31000 \
  --attention-backend torch_sdpa \
  --enable-torch-compile \
  --warmup-resolutions 1024x1024 \
  --warmup-steps 1
```

Request: `1024x1024`, `num_inference_steps=1`, `guidance_scale=0.0`.

Observed cold warmup and first external request:
- cold server warmup request: `123.75s`
- internal real-path prewarm denoise: `1.0928s`, then `0.0220s`
- first external real request after ready: wall `0.383s`, `DenoisingStage 0.0315s`, `DecodingStage 0.0098s`

Note: `torch_sdpa` was used only because this H100 validation environment has a local FA3 binding mismatch in the text encoder path; this PR does not depend on SDPA.



































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28694204030](https://github.com/sgl-project/sglang/actions/runs/28694204030)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28694203997](https://github.com/sgl-project/sglang/actions/runs/28694203997)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
