---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] fix: fix z-Image online fp8 quantization crash with dit_cpu_offload'
canonical_url: https://github.com/sgl-project/sglang/pull/29903
captured_at: '2026-07-05T02:14:10.241720+00:00'
content_hash: 3a344bf1e3411ffcb4549947d2764f747f04d61626842933224bb826d51539d2
---
# [diffusion] fix: fix z-Image online fp8 quantization crash with dit_cpu_offload

URL: https://github.com/sgl-project/sglang/pull/29903
State: closed
Labels: quant, run-ci, diffusion
Closed at: 2026-07-04T15:40:44Z
Merged at: 2026-07-04T15:40:44Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

`sglang generate --model-path Tongyi-MAI/Z-Image-Turbo --quantization fp8` crashes with `TypeError: 'NoneType' object is not callable` in `zimage.py::get_freqs_cis`. Online fp8 for Z-Image-Turbo is a documented "validated" path, so this is a regression.

Cause: the auto memory policy enables `dit_cpu_offload`, leaving DiT weights on CPU. Online fp8 quantizes at load time via a CUDA/NPU-only kernel, which fails on CPU tensors. The loader then silently falls back to a native diffusers model (no `rotary_emb`), and denoising crashes calling `rotary_emb(None)`.

closes #29833

## Modifications

- `transformer_load_utils.py`: disable `dit_cpu_offload` when online quantization is requested (not just `modelopt_fp8`), so the DiT stays on device for the load-time quant kernel. `--dit-layerwise-offload` remains the way to save DiT memory.
- `transformer_loader.py`: a failed quantized load now raises the real error instead of silently falling back to an unquantized native model.
- `zimage.py`: `get_freqs_cis` raises a clear error when `rotary_emb` is `None`.

## Accuracy Tests

Loader fix, not a kernel/forward change. 
Before: crashes on the first denoise step. 
After: loads `ZImageTransformer2DModel (sgl-diffusion version)`, no native fallback, image generated correctly.



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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28709134335](https://github.com/sgl-project/sglang/actions/runs/28709134335)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28709134305](https://github.com/sgl-project/sglang/actions/runs/28709134305)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
