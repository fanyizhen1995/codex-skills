---
source_id: sglang-github-closed-issues-prs
title: Fix image URL response for multiple outputs
canonical_url: https://github.com/sgl-project/sglang/pull/30621
captured_at: '2026-07-15T23:40:28.369710+00:00'
content_hash: 4c4a356edbf168602d1188388312ad97f23b252a5e650016e48b7588c676c07b
---
# Fix image URL response for multiple outputs

URL: https://github.com/sgl-project/sglang/pull/30621
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-15T11:49:05Z
Merged at: 2026-07-15T11:49:05Z

Closes #30648

## Summary

Fix OpenAI image API URL responses when a request generates multiple output images.

Previously, `response_format="url"` only returned one URL even when the pipeline produced multiple output files. This updates the response path to return one `data` item per output image, matching the behavior of `b64_json`.

This also adds local fallback URL support for multiple persisted outputs by using `variant` query parameters, so each generated image can be downloaded through `/v1/images/{id}/content?variant={idx}` when cloud storage is not configured.

## Changes

- Upload and track all generated output files instead of only the first one.
- Return one URL response item per generated image.
- Store `file_paths`, `urls`, and `num_outputs` in `IMAGE_STORE`.
- Add `variant` support to the image content download endpoint.
- Avoid `AttributeError` for optional progressive fields when the request schema does not define them.
- Add unit coverage for multi-output URL responses and variant path selection.

## Testing

- `PYTHONPATH=python python -m pytest --noconftest python/sglang/multimodal_gen/test/unit/test_openai_image_api.py -q`
- `python -m py_compile python/sglang/multimodal_gen/runtime/entrypoints/openai/image_api.py python/sglang/multimodal_gen/test/unit/test_openai_image_api.py`
- Manual verification with `response_format="url"` and `n=2`

























































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29396207334](https://github.com/sgl-project/sglang/actions/runs/29396207334)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29396207224](https://github.com/sgl-project/sglang/actions/runs/29396207224)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
