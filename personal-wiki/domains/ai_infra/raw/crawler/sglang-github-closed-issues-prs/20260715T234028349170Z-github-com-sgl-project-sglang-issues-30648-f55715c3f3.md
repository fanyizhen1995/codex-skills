---
source_id: sglang-github-closed-issues-prs
title: '[Bug] OpenAI image API returns only one URL when `n > 1` and `response_format="url"`'
canonical_url: https://github.com/sgl-project/sglang/issues/30648
captured_at: '2026-07-15T23:40:28.349170+00:00'
content_hash: f55715c3f3cc0b887a56537cf6b2655d83ff5b6b9dd14f11d798f89a3d41bf4a
---
# [Bug] OpenAI image API returns only one URL when `n > 1` and `response_format="url"`

URL: https://github.com/sgl-project/sglang/issues/30648
State: closed
Labels: 
Closed at: 2026-07-15T11:49:06Z
Merged at: 

### Checklist

- [ ] I searched related issues but found no solution.
- [ ] The bug persists in the latest version.
- [ ] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [ ] Please use English. Otherwise, it will be closed.

### Describe the bug


When using the OpenAI-compatible image generation API with `response_format="url"` and `n > 1`, the backend can generate and save multiple output images, but the HTTP response only returns one item in `data`.

This makes URL-format responses inconsistent with `b64_json`, where one response item is returned per generated image.


### Reproduction

Send an image generation request with `n=2` and `response_format="url"`:

```python
import requests

response = requests.post(
    "http://127.0.0.1:30010/v1/images/generations",
    json={
        "prompt": "a test prompt",
        "size": "512x512",
        "response_format": "url",
        "seed": 42,
        "n": 2,
    },
)

resp_json = response.json()
print("num data:", len(resp_json["data"]))
print(resp_json)
```
Expected Behavior
The response should contain one data item per generated image:

> {
>   "data": [
>     {"url": "...variant=0"},
>     {"url": "...variant=1"}
>   ]
> }

Actual Behavior
Only one URL is returned：

> num data: 1

Even though the server logs show multiple output files were generated and saved.

Scope
This is not specific to ideogram. It affects any model that successfully generates multiple images and uses response_format="url" through the OpenAI image API path.
b64_json responses are not affected because they already iterate over all saved output paths.

### Environment

model:ideogram
gpu
