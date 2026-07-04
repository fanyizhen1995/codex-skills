---
source_id: sglang-github-closed-issues-prs
title: '[diffusion][cache-dit] add cache-dit support for Ideogram 4'
canonical_url: https://github.com/sgl-project/sglang/pull/29631
captured_at: '2026-07-04T02:13:49.133327+00:00'
content_hash: 7e93b1cf2923a32ee84f6255a2b6d5a740e716c0760d9629ea2cc1d763d7edf8
---
# [diffusion][cache-dit] add cache-dit support for Ideogram 4

URL: https://github.com/sgl-project/sglang/pull/29631
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-03T11:58:48Z
Merged at: 2026-07-03T11:58:48Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Add Cache-DiT support for Ideogram 4 in SGLang.

Ideogram 4 uses two DiT modules: a conditional transformer and an unconditional transformer. This PR enables optional Cache-DiT acceleration for both transformers through the existing `SGLANG_CACHE_DIT_ENABLED` flag. The default path is unchanged when Cache-DiT is disabled.


<!-- Describe the purpose and goals of this pull request. -->

## Modifications
- Add Ideogram 4 dual-transformer Cache-DiT support.
  - Use `layers` and `ForwardPattern.Pattern_3` for both conditional and unconditional transformers.
  - Set `has_separate_cfg=False` because Ideogram 4 uses separate conditional/unconditional transformer modules.

- Reuse the shared `DenoisingStage._maybe_enable_cache_dit` path for Ideogram 4.
  - Pass the unconditional transformer as `transformer_2`.
  - Add `DualTransformerExecutionMode` so Wan2.2 keeps boundary-expert behavior while Ideogram 4 uses paired-per-step behavior.
  - Reuse shared setup/refresh/SCM/distributed-group/torch.compile handling.

<!-- Detail the changes made in this pull request. -->

## Accuracy Tests
Cache-DiT is disabled by default, so the default Ideogram 4 path is unchanged.

Manual smoke test with Cache-DiT enabled generated valid images successfully. Since Cache-DiT is an approximate feature-caching optimization, exact pixel equality with the non-cached path is not expected.

Test command:

```bash
SGLANG_CACHE_DIT_ENABLED=true \
SGLANG_CACHE_DIT_FN=1 \
SGLANG_CACHE_DIT_BN=0 \
SGLANG_CACHE_DIT_WARMUP=4 \
SGLANG_CACHE_DIT_MC=3 \
SGLANG_CACHE_DIT_RDT=0.24 \
sglang serve \
  --model-path /upfs/models/ideogram-ai/ideogram-4-fp8 \
  --model-type diffusion \
  --num-gpus 1 \
  --performance-mode speed \
  --host 0.0.0.0 \
  --port 30010 \
  --enable-torch-compile
```

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling
Test setup:

- GPU: NVIDIA B200
- Model: Ideogram 4 FP8
- Preset: `V4_DEFAULT_20`
- Steps: 20
- Resolution: 1024x1024
- Serving mode: `--performance-mode speed`
- Torch compile: enabled

Result for single-image generation:

| Setting | Latency |
| --- | ---: |
| Baseline | 3.55s |
| Cache-DiT enabled | 1.66s |

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28637046348](https://github.com/sgl-project/sglang/actions/runs/28637046348)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28637046286](https://github.com/sgl-project/sglang/actions/runs/28637046286)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
