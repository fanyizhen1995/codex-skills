---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] model: support LongLive 2.0 T2V and I2V inference'
canonical_url: https://github.com/sgl-project/sglang/pull/27639
captured_at: '2026-07-14T23:40:21.690068+00:00'
content_hash: 4a244475fcb136be5b99f726c3b3fdad419235b8c094cc7bc74730fd3588c44d
---
# [diffusion] model: support LongLive 2.0 T2V and I2V inference

URL: https://github.com/sgl-project/sglang/pull/27639
State: closed
Labels: documentation, run-ci, diffusion
Closed at: 2026-07-14T00:39:31Z
Merged at: 2026-07-14T00:39:31Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

This PR adds SGLang Diffusion support for [LongLive 2.0](https://github.com/NVlabs/LongLive). LongLive 2.0 is a causal long-video generation model based on Wan2.2-TI2V-5B. This integration focuses on the BF16 text-to-video inference path, including LongLive-specific causal block execution and multi-shot inference behavior. LongLive 2.0 does not currently have an official Diffusers release, so this PR registers both the converted Diffusers-style HF repo and the original model:
- [Rabinovich/LongLive-2.0-5B-Diffusers](https://huggingface.co/Rabinovich/LongLive-2.0-5B-Diffusers) (personally converted version)
- [Efficient-Large-Model/LongLive-2.0-5B](https://huggingface.co/Efficient-Large-Model/LongLive-2.0-5B) (official version)

Not included for now:
- NVFP4 inference and NVFP4 KV-Cache
- Ulysses sequence-parallel inference
- Async VAE Decoding

More importantly, this is also an exploratory for providing unified support for AR video generation in SGLang-Diffusion in the future.

Refer to issue: https://github.com/sgl-project/sglang/issues/23578

## Modifications
- Add LongLive 2.0 model registration, pipeline config, sampling params, and DiT checkpoint parameter mappings.
- Add a LongLive2 T2V pipeline built on the existing Wan causal DMD pipeline.
- Add LongLive-specific causal denoising support for 8-frame blocks, multi-shot prompts, shot-aware KV-cache sinks, RoPE temporal offsets, and CFG.
- Reuse the standard SGLang text encoding, scheduling, latent preparation, and decoding flow where possible.

## Accuracy Tests
Note: all of these test are running on a DGX Spark with identical parameter and seed:
Prompt (from official website: https://nvlabs.github.io/LongLive/LongLive2/):
```
Shot Prompts
Shot 1
A husky licks crumbs from its nose in a cozy red room.
Shot 2
A fluffy dog plays on the carpet near a person in the living room.
Shot 3
The dog moves to a doorway and receives a gentle pat.
Shot 4
The dog looks up alertly in a sunlit hallway near the stairs.
Shot 5
A husky follows the camera from the hallway into a bathroom.
Shot 6
A hand places a treat on the husky's snout, and the dog licks it off.
Shot 7
Two fluffy dogs hurry through the doorway, one following the other.
Shot 8
A cream-colored dog trots down the hallway while a smaller dog appears nearby.
```

Original:
https://github.com/user-attachments/assets/e2660b8c-3a58-493f-acc5-405a72d1364e

SGLang:

https://github.com/user-attachments/assets/5e36142e-33d3-40f3-a6d5-716278283e79


## Speed Tests and Profiling

Not run yet (I will test it later)

Example test command:
```bash
sglang generate \
  --model-path Rabinovich/LongLive-2.0-5B-Diffusers \
  --prompt "A cinematic shot of a red sports car driving along a coastal road at sunset." \
  --height 704 \
  --width 1280 \
  --num-frames 61 \
  --num-inference-steps 4 \
  --perf-dump-path longlive2_sglang.json
```

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29151062081](https://github.com/sgl-project/sglang/actions/runs/29151062081)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29151062040](https://github.com/sgl-project/sglang/actions/runs/29151062040)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
