---
source_id: sglang-github-closed-issues-prs
title: '[Diffusion] Diffusion model support log-requests'
canonical_url: https://github.com/sgl-project/sglang/pull/23049
captured_at: '2026-07-06T02:14:53.062075+00:00'
content_hash: a9bd72d23d7dfaa6855faab70904adad510c98836b6895c47eea164c87797285
---
# [Diffusion] Diffusion model support log-requests

URL: https://github.com/sgl-project/sglang/pull/23049
State: closed
Labels: documentation, run-ci, diffusion
Closed at: 2026-07-05T09:01:26Z
Merged at: 2026-07-05T09:01:26Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

Diffusion model serving (image/video generation) did not support `--log-requests`, `--log-requests-level`, `--log-requests-format`, or `--log-requests-target`, so these flags were rejected at startup. The LLM serving path already had full support via `RequestLogger` in `srt/utils/request_logger.py`. This PR brings equivalent request logging to the diffusion runtime, mirroring srt's `RequestLogger` design.

#21826 (log-requests part)
Roadmap: #18967

## Modifications

<!-- Detail the changes made in this pull request. -->

1. **New `DiffusionRequestLogger`** (`runtime/utils/request_logger.py`) that mirrors srt's `RequestLogger`:
   - **Sampling-config whitelist** (`_SAMPLING_CONFIG_FIELDS`, 10 fields: `data_type, seed, num_inference_steps, guidance_scale, true_cfg_scale, width, height, num_frames, fps, num_outputs_per_prompt`). Diffusion `Req` / `SamplingParams` dataclasses have 50+ fields including internal tensors (`prompt_embeds`, `latents`, `noise_pred`, `output`, …), a whitelist keeps the log user-facing and clean.
   - **Two hooks**, `log_received_request(batch)` and `log_finished_request(batch, result)`, matching srt's API.
   - **Level semantics** (gated by `--log-requests-level`):
     - `0`: request id only.
     - `1`: + sampling config (the 10 fields above).
     - `2`: + prompt / negative prompt (truncated to 2 KiB).
     - `3`: + full prompt / negative prompt.

2. **Hook placement in `SchedulerClient`** (`runtime/scheduler_client.py`): the two hooks are called inside `SchedulerClient.forward()` and `AsyncSchedulerClient.forward()` — the request↔scheduler blocking point — so each forward call emits exactly one received and one finished record.

3. **CLI flags** (`runtime/server_args.py`): `--log-requests`, `--log-requests-level {0|1|2|3}` (default `2`), `--log-requests-format {text|json}` (default `text`), `--log-requests-target {TARGET...}` (`stdout` and/or directory paths).

4. **Docs** (`docs_new/docs/sglang-diffusion/api/cli.mdx`): added a `### Request logging` section under `## Common Options`.


## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

### image case (model: `Efficient-Large-Model/Sana_600M_512px_diffusers`)

`TestImageRequestLoggerText` (text format):
```
[2026-06-30 09:14:38] Receive: obj={'request_id': '6ef3fb55-a97c-4c92-87c5-b8f1fb7735da', 'sampling_params': {'data_type': DataType.IMAGE, 'seed': 42, 'num_inference_steps': 20, 'guidance_scale': 4.5, 'true_cfg_scale': None, 'width': 256, 'height': 256, 'num_frames': 1, 'fps': 24, 'num_outputs_per_prompt': 1}, 'prompt': 'A beautiful sunset over mountains, oil painting style', 'negative_prompt': 'low quality, low resolution, blurry, overexposed, underexposed, distorted, deformed, disfigured, bad anatomy, extra limbs, watermark, text, signature, ugly, noisy, artifacts'}

[2026-06-30 09:14:41] Finish: obj={'request_id': '6ef3fb55-a97c-4c92-87c5-b8f1fb7735da', 'sampling_params': {'data_type': DataType.IMAGE, 'seed': 42, 'num_inference_steps': 20, 'guidance_scale': 4.5, 'true_cfg_scale': None, 'width': 256, 'height': 256, 'num_frames': 1, 'fps': 24, 'num_outputs_per_prompt': 1}, 'prompt': 'A beautiful sunset over mountains, oil painting style', 'negative_prompt': 'low quality, low resolution, blurry, overexposed, underexposed, distorted, deformed, disfigured, bad anatomy, extra limbs, watermark, text, signature, ugly, noisy, artifacts'}, out={'meta_info': {'e2e_latency': 2.718243174997042}, 'error': None}
```

`TestImageRequestLoggerJson` (json format):
```
[2026-06-30 09:15:47] {"timestamp": "2026-06-30T09:15:47.282730", "event": "request.received", "rid": "ff61568f-f577-468f-afde-ea1aab475acc", "obj": {"request_id": "ff61568f-f577-468f-afde-ea1aab475acc", "sampling_params": {"data_type": "DataType.IMAGE", "seed": 42, "num_inference_steps": 20, "guidance_scale": 4.5, "true_cfg_scale": null, "width": 256, "height": 256, "num_frames": 1, "fps": 24, "num_outputs_per_prompt": 1}, "prompt": "A beautiful sunset over mountains, oil painting style", "negative_prompt": "low quality, low resolution, blurry, overexposed, underexposed, distorted, deformed, disfigured, bad anatomy, extra limbs, watermark, text, signature, ugly, noisy, artifacts"}}

[2026-06-30 09:15:50] {"timestamp": "2026-06-30T09:15:50.214678", "event": "request.finished", "rid": "ff61568f-f577-468f-afde-ea1aab475acc", "obj": {"request_id": "ff61568f-f577-468f-afde-ea1aab475acc", "sampling_params": {"data_type": "DataType.IMAGE", "seed": 42, "num_inference_steps": 20, "guidance_scale": 4.5, "true_cfg_scale": null, "width": 256, "height": 256, "num_frames": 1, "fps": 24, "num_outputs_per_prompt": 1}, "prompt": "A beautiful sunset over mountains, oil painting style", "negative_prompt": "low quality, low resolution, blurry, overexposed, underexposed, distorted, deformed, disfigured, bad anatomy, extra limbs, watermark, text, signature, ugly, noisy, artifacts"}, "out": {"meta_info": {"e2e_latency": 2.8768238479970023}, "error": null}}
```

### video case (model: `Wan-AI/Wan2.1-T2V-1.3B-Diffusers`)

`TestVideoRequestLoggerText` (text format):
```
[2026-06-30 09:17:05] Receive: obj={'request_id': '5d6089f0-dc0f-466d-a95d-17d40f3a7c0f', 'sampling_params': {'data_type': DataType.VIDEO, 'seed': 42, 'num_inference_steps': 10, 'guidance_scale': 3.0, 'true_cfg_scale': None, 'width': 832, 'height': 480, 'num_frames': 5, 'fps': 24, 'num_outputs_per_prompt': 1}, 'prompt': 'A cat playing with a ball', 'negative_prompt': 'Bright tones, overexposed, static, blurred details, subtitles, style, works, paintings, images, static, overall gray, worst quality, low quality, JPEG compression residue, ugly, incomplete, extra fingers, poorly drawn hands, poorly drawn faces, deformed, disfigured, misshapen limbs, fused fingers, still picture, messy background, three legs, many people in the background, walking backwards'}

[2026-06-30 09:17:14] Finish: obj={'request_id': '5d6089f0-dc0f-466d-a95d-17d40f3a7c0f', 'sampling_params': {'data_type': DataType.VIDEO, 'seed': 42, 'num_inference_steps': 10, 'guidance_scale': 3.0, 'true_cfg_scale': None, 'width': 832, 'height': 480, 'num_frames': 5, 'fps': 24, 'num_outputs_per_prompt': 1}, 'prompt': 'A cat playing with a ball', 'negative_prompt': 'Bright tones, overexposed, static, blurred details, subtitles, style, works, paintings, images, static, overall gray, worst quality, low quality, JPEG compression residue, ugly, incomplete, extra fingers, poorly drawn hands, poorly drawn faces, deformed, disfigured, misshapen limbs, fused fingers, still picture, messy background, three legs, many people in the background, walking backwards'}, out={'meta_info': {'e2e_latency': 8.437134762993082}, 'error': None}
```

`TestVideoRequestLoggerJson` (json format):
```
[2026-06-30 09:18:30] {"timestamp": "2026-06-30T09:18:30.974658", "event": "request.received", "rid": "7547dcb2-7268-4a16-a2a4-731a503a53a1", "obj": {"request_id": "7547dcb2-7268-4a16-a2a4-731a503a53a1", "sampling_params": {"data_type": "DataType.VIDEO", "seed": 42, "num_inference_steps": 10, "guidance_scale": 3.0, "true_cfg_scale": null, "width": 832, "height": 480, "num_frames": 5, "fps": 24, "num_outputs_per_prompt": 1}, "prompt": "A cat playing with a ball", "negative_prompt": "Bright tones, overexposed, static, blurred details, subtitles, style, works, paintings, images, static, overall gray, worst quality, low quality, JPEG compression residue, ugly, incomplete, extra fingers, poorly drawn hands, poorly drawn faces, deformed, disfigured, misshapen limbs, fused fingers, still picture, messy background, three legs, many people in the background, walking backwards"}}

[2026-06-30 09:18:40] {"timestamp": "2026-06-30T09:18:40.151854", "event": "request.finished", "rid": "7547dcb2-7268-4a16-a2a4-731a503a53a1", "obj": {"request_id": "7547dcb2-7268-4a16-a2a4-731a503a53a1", "sampling_params": {"data_type": "DataType.VIDEO", "seed": 42, "num_inference_steps": 10, "guidance_scale": 3.0, "true_cfg_scale": null, "width": 832, "height": 480, "num_frames": 5, "fps": 24, "num_outputs_per_prompt": 1}, "prompt": "A cat playing with a ball", "negative_prompt": "Bright tones, overexposed, static, blurred details, subtitles, style, works, paintings, images, static, overall gray, worst quality, low quality, JPEG compression residue, ugly, incomplete, extra fingers, poorly drawn hands, poorly drawn faces, deformed, disfigured, misshapen limbs, fused fingers, still picture, messy background, three legs, many people in the background, walking backwards"}, "out": {"meta_info": {"e2e_latency": 8.351047667994862}, "error": null}}
```

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

N/A

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28733285535](https://github.com/sgl-project/sglang/actions/runs/28733285535)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28733285455](https://github.com/sgl-project/sglang/actions/runs/28733285455)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
