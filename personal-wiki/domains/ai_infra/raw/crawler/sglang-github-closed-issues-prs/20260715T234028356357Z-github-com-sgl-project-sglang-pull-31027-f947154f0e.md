---
source_id: sglang-github-closed-issues-prs
title: '[Multimodal] Support n>1 outputs for GLM-Image generation'
canonical_url: https://github.com/sgl-project/sglang/pull/31027
captured_at: '2026-07-15T23:40:28.356357+00:00'
content_hash: f947154f0ea1e62ffcf3e96d35ea4ea1b03666b6ea20a34c3208b01e717ff96a
---
# [Multimodal] Support n>1 outputs for GLM-Image generation

URL: https://github.com/sgl-project/sglang/pull/31027
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-15T17:55:20Z
Merged at: 2026-07-15T17:55:20Z

## Motivation

GLM-Image requests with `num_outputs_per_prompt > 1` / OpenAI image API `n > 1` currently only produce one image.

GLM-Image has a model-specific AR prior stage that generates image tokens before denoising. Unlike standard T2I pipelines, simply relying on downstream latent batching is not enough because the AR prior, prompt/glyph embeddings, latents, size conditions, and prior-token tensors must all agree on the effective output batch size.

This PR adds GLM-Image multi-output support so a single prompt can produce multiple images in one request.

## Modifications

- Add GLM-Image helpers to resolve per-request output count, per-output seeds, and batch-dimension expansion.
- Update `GlmImageAR` to generate one AR prior token sequence per requested output and concatenate them along batch dimension.
- Update `GlmImageBeforeDenoisingStage` to align:
  - `prior_token_id`
  - prompt / negative prompt embeddings
  - latents
  - `target_size`
  - `crop_coords`
  - reference-image condition tensors
  with `num_outputs_per_prompt`.
- Add NPU-specific fallback in `GlmImageTransformer2DModel.forward` for `batch_size > 1` without KV cache:
  - split the batch into single-sample forwards
  - concatenate outputs back along batch dimension
  - avoid unsupported or fragile NPU batch execution paths.
- Make selected tensor reshapes use `.reshape(...)` instead of `.view(...)` where non-contiguous tensors may appear.
- Improve NPU layernorm scale-shift handling:
  - use fused `scale_shift` only for supported modulation shapes
  - fallback to native `normalized * (1 + scale) + shift` when fused kernel shape constraints are not met.
- Add unit tests for:
  - AR prior generation per requested output
  - before-denoising batch expansion
  - NPU transformer fallback behavior

## Accuracy Tests

Not run in a full model environment in this local workspace.

Recommended validation:
- Start GLM-Image on NPU.
- Send an OpenAI image generation request with `n: 2`.
- Verify the response contains 2 images.
- Verify the two outputs use different per-output seeds when a scalar seed is provided.

Example request shape:

```json
{
  "model": "glm-image",
  "prompt": "a cat sitting on a chair",
  "n": 2,
  "size": "1024x1024",
  "seed": 11
}
```
<img width="1719" height="832" alt="3444a257bdc5f40100467249334cad11" src="https://github.com/user-attachments/assets/c50c475b-b313-46f5-9961-cfcf15d7ab70" />


Closes #30510



























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29403757586](https://github.com/sgl-project/sglang/actions/runs/29403757586)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29403757256](https://github.com/sgl-project/sglang/actions/runs/29403757256)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
