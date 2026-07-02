---
source_id: sglang-github-closed-issues-prs
title: Fix Nunchaku FP4 validation and image save output
canonical_url: https://github.com/sgl-project/sglang/pull/29612
captured_at: '2026-07-01T02:12:08.970442+00:00'
content_hash: b5c66d0ae2498a1c93da42dede88be4d99ee33b34e444507a69eb289f6a625da
---
# Fix Nunchaku FP4 validation and image save output

URL: https://github.com/sgl-project/sglang/pull/29612
State: closed
Labels: quant, diffusion
Closed at: 2026-06-30T00:04:23Z
Merged at: 

## Motivation

Related to #28256. The report has two actionable parts:

- Nunchaku SVDQuant FP4 weights can be inferred from `svdq-fp4_*` filenames and pass SGLang startup validation on non-Blackwell devices, then fail later inside the external Nunchaku CUDA path with a less actionable runtime error.
- The OpenAI-compatible image endpoint accepts extension fields such as `extra_body={"save_output": false}`, but image generation still uses the server default output directory and persists files.

This PR does not make FP4 supported on non-Blackwell GPUs; it makes that unsupported configuration fail earlier with a clearer message and preserves INT4 behavior.

## Modifications

- Reject Nunchaku SVDQuant FP4 on non-Blackwell GPU capabilities during argument validation, while keeping INT4 support for SM8x and allowing FP4 on SM10x/SM12x Blackwell.
- Add `save_output` and `output_path` fields to `ImageGenerationsRequest`.
- Resolve image output paths per request: `save_output=false` uses a temporary output path for response materialization and avoids persistent local output for `b64_json` responses.
- Add focused unit coverage for the Nunchaku capability guard and image output path resolution, including nested `extra_body`.

## Accuracy Tests

Not applicable. This changes validation and response file persistence behavior; it does not change model forward math or generated image contents.

## Speed Tests and Profiling

Not applicable. No request-path compute kernels or scheduling behavior are changed.

## Tests

- `git diff --check`
- On an H200 validation VM using `lmsysorg/sglang:latest`:
  `PYTHONPATH=python python3 -m pytest python/sglang/multimodal_gen/test/unit/test_openai_image_api.py python/sglang/multimodal_gen/test/unit/test_openai_utils.py python/sglang/multimodal_gen/test/unit/test_nunchaku_quantization_args.py -q`
  Result: `13 passed`

Full Nunchaku Z-Image FP4 runtime was not run in this PR validation because the available SGLang container does not include the external `nunchaku` package and the B200 host did not already have the image/model cache. The FP4 change is covered at the SGLang validation boundary with mocked CUDA capabilities.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations). (N/A)
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed). (N/A)
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28348804199](https://github.com/sgl-project/sglang/actions/runs/28348804199)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28348804083](https://github.com/sgl-project/sglang/actions/runs/28348804083)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
