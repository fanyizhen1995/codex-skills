---
source_id: sglang-github-closed-issues-prs
title: Fix Ministral3 accuracy issue by aligning YaRN RoPE scaling with Transformers
  implementation
canonical_url: https://github.com/sgl-project/sglang/pull/31232
captured_at: '2026-07-15T23:40:28.369381+00:00'
content_hash: 446d580d9a37e9d4743e1e37c1fc1ab0e45bcd3d79e59ee203cfc680a194d70e
---
# Fix Ministral3 accuracy issue by aligning YaRN RoPE scaling with Transformers implementation

URL: https://github.com/sgl-project/sglang/pull/31232
State: closed
Labels: run-ci
Closed at: 2026-07-15T12:23:05Z
Merged at: 2026-07-15T12:23:05Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

The current YaRN RoPE scaling implementation in SGLang does not fully match the Transformers implementation. In particular, it does not handle the `mscale` and `mscale_all_dim` parameters from `rope_scaling`, which leads to different RoPE scaling behavior.

This mismatch causes accuracy degradation for YaRN-based models such as Ministral3, where SGLang generation produces significantly lower accuracy compared with the Transformers implementation.

<!-- Describe the purpose and goals of this pull request. -->

## Modifications

Added `mscale` and `mscale_all_dim` parameters to the `YaRNScalingRotaryEmbedding` constructor to accept corresponding `rope_scaling` configuration values.
Added Transformers-compatible YaRN scaling logic ([YaRN scaling logic](https://github.com/huggingface/transformers/blob/63f32a8782cb70da3365acab16f2b67947737985/src/transformers/modeling_rope_utils.py#L412)) to recompute `mscale` when `mscale` and `mscale_all_dim` are provided.
 

<!-- Detail the changes made in this pull request. -->

## Accuracy Tests

Model:
`mistralai/Ministral-3-14B-Instruct-2512-BF16`

### Transformers Implementation

Server:
`sglang serve --model-path mistralai/Ministral-3-14B-Instruct-2512-BF16 --tp-size 4 --model-impl transformers `

| Benchmark | Accuracy |
|-----------|----------|
| GSM8K     | 0.925    |
| MMMU      | Failed   |


### SGLang Implementation

Server:
`sglang serve --model-path mistralai/Ministral-3-14B-Instruct-2512-BF16 --tp-size 4`

Accuracy:

| Benchmark | Accuracy Before Fix | Accuracy After Fix |
|-----------|------------|-----------|
| GSM8K     | 0.860      | 0.920     |
| MMMU      | 0.483      | 0.523     |



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

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29394580454](https://github.com/sgl-project/sglang/actions/runs/29394580454)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29394580343](https://github.com/sgl-project/sglang/actions/runs/29394580343)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
