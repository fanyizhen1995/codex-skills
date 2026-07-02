---
source_id: sglang-github-closed-issues-prs
title: '[NPU] Fix glm 4.6v'
canonical_url: https://github.com/sgl-project/sglang/pull/29381
captured_at: '2026-07-02T02:12:27.265203+00:00'
content_hash: cca816e7618b93bf6243521382e28218caa6378a425fb9f6684662f165a8fb97
---
# [NPU] Fix glm 4.6v

URL: https://github.com/sgl-project/sglang/pull/29381
State: closed
Labels: run-ci
Closed at: 2026-07-01T07:13:48Z
Merged at: 2026-07-01T07:13:48Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->
fix glm 4.6v processor

before this pr:

File "/sglang/python/sglang/srt/multimodal/processors/base_processor.py", line 467, in process_mm_data
    result = processor.__call__(
             ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.15/lib/python3.11/site-packages/transformers/models/glm46v/processing_glm46v.py", line 92, in __call__
    image_inputs = self.image_processor(images=images, **output_kwargs["images_kwargs"])
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sglang/python/sglang/srt/utils/hf_transformers_patches.py", line 263, in safe_call
    return original(self, images, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.15/lib/python3.11/site-packages/transformers/image_processing_utils.py", line 217, in __call__
    return self.preprocess(images, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.15/lib/python3.11/site-packages/transformers/models/glm46v/image_processing_glm46v.py", line 112, in preprocess
    return super().preprocess(images, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.15/lib/python3.11/site-packages/transformers/image_processing_utils.py", line 402, in preprocess
    return self._preprocess_image_like_inputs(images, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.15/lib/python3.11/site-packages/transformers/image_processing_utils.py", line 314, in _preprocess_image_like_inputs
    return self._preprocess(images, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: npu_wrapper_glm46v_preprocess.<locals>._preprocess() missing 1 required positional argument: 'interpolation'
## Modifications

<!-- Detail the changes made in this pull request. -->
replace interpolation with resample due to upstream change
## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28218348866](https://github.com/sgl-project/sglang/actions/runs/28218348866)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28218348783](https://github.com/sgl-project/sglang/actions/runs/28218348783)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
