---
source_id: sglang-github-closed-issues-prs
title: '[Bug] GLM-image /v1/images/generations ignores n > 1 and returns only one
  image'
canonical_url: https://github.com/sgl-project/sglang/issues/30510
captured_at: '2026-07-15T23:40:28.348348+00:00'
content_hash: 6de6fa534609945dfec0f21a5343276d46028384d8183c7287ce65aef6b444b6
---
# [Bug] GLM-image /v1/images/generations ignores n > 1 and returns only one image

URL: https://github.com/sgl-project/sglang/issues/30510
State: closed
Labels: 
Closed at: 2026-07-15T17:55:21Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

When serving a GLM-image model through the OpenAI-compatible image generation endpoint, a request with `n: 2` returns only one generated image in `response.data`.

The request is sent to:

`POST /v1/images/generations`

with `response_format: "b64_json"` and `n: 2`.

Expected behavior:
The response should contain two image items in `response.data`.

Actual behavior:
The response contains only one image item.

From code inspection on latest `main`, the image API correctly maps `n` to `num_outputs_per_prompt` in `python/sglang/multimodal_gen/runtime/entrypoints/openai/image_api.py`. However, the GLM-image model-specific pipeline appears to execute only a single sample:

- `GlmImageAR._extract_large_image_tokens()` uses `outputs[0]`, so only the first AR generation is consumed.
- `GlmImageBeforeDenoisingStage.forward()` calls `prepare_latents(batch_size=1, ...)`, so only one latent sample is prepared.
- The single request path does not expand `num_outputs_per_prompt` into multiple per-output requests before scheduler execution.

This makes `n > 1` ineffective for GLM-image.

### Reproduction

Run a GLM-image server, then send:

```python
import requests

prompt = "a beautiful landscape"

response = requests.post(
    "http://127.0.0.1:8898/v1/images/generations",
    json={
        "prompt": prompt,
        "size": "960x1728",
        "num_inference_steps": 30,
        "response_format": "b64_json",
        "seed": 42,
        "n": 2,
    },
)

payload = response.json()
print(response.status_code)
print(len(payload["data"]))
print(payload.keys())

### Environment

npu 910b3
