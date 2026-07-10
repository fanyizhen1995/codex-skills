---
source_id: sglang-github-closed-issues-prs
title: '[diffusion]: enable RL rollout path for LTX-2.3 post-training'
canonical_url: https://github.com/sgl-project/sglang/pull/28926
captured_at: '2026-07-09T23:36:35.341281+00:00'
content_hash: a16af0cf190fbaad1a286e472f60cf2eb2ced796a6676bb0649c940b14914f0d
---
# [diffusion]: enable RL rollout path for LTX-2.3 post-training

URL: https://github.com/sgl-project/sglang/pull/28926
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-09T02:24:06Z
Merged at: 2026-07-09T02:24:06Z

## Motivation

LTX-2/2.3 joint audio-video generation uses a custom stage-1 guider and the diffusers `FlowMatchEulerDiscreteScheduler` by default. These paths work for standard inference, but they are incompatible with the existing diffusion **RL rollout** pipeline (`/rollout/generate`), which expects:

1. Standard classifier-free guidance via `guidance_scale` (typically `1.0` for LTX RL), not the LTX-2.3 stage-1 guider.
2. SGLang's SDE-aware `scheduler.step(..., batch=...)` so rollout can inject stochastic dynamics and collect per-step log-probs / trajectories.
3. `rollout_trajectory_data` to survive the full LTX AV pipeline (denoising → decoding).
4. Correct serialization of decoded video, which is returned as `numpy` arrays rather than `torch.Tensor`.

This PR adds a minimal, LTX-specific rollout path so LTX-2.3 can be used as a rollout backend for RL post-training frameworks (e.g. [miles_diffusion](https://github.com/radixark/miles_diffusion)). Non-rollout inference behavior is unchanged.

## Modifications

**6 files, +32 / −5 lines.** All rollout-specific logic is gated on `batch.rollout` or `sampling_params.rollout`.

| Area | Change |
|------|--------|
| `configs/sample/ltx_2.py` | Skip injecting `ltx2_stage1_guider_params` during rollout; RL uses `guidance_scale=1` + standard CFG. |
| `pipelines/ltx_2_pipeline.py` | Use SGLang's `FlowMatchEulerDiscreteScheduler` instead of diffusers', enabling SDE rollout dynamics (`batch` kwarg in `step`). |
| `stages/model_specific_stages/ltx_2/denoising.py` | During rollout, route video denoising through SDE `scheduler.step` with `generator` / `eta` / `batch` kwargs and explicit `_step_index`. |
| `stages/model_specific_stages/ltx_2/decoding_av.py` | Forward `rollout_trajectory_data` through `OutputBatch` so trajectory/log-prob data reaches the rollout API. |
| `entrypoints/post_training/rollout_api.py` | Avoid calling `.contiguous()` on non-tensor outputs (LTX decoded video is `numpy`). |
| `entrypoints/post_training/utils.py` | Serialize `numpy.ndarray` outputs in rollout HTTP responses. |
## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.



















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28914342058](https://github.com/sgl-project/sglang/actions/runs/28914342058)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28914342011](https://github.com/sgl-project/sglang/actions/runs/28914342011)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
