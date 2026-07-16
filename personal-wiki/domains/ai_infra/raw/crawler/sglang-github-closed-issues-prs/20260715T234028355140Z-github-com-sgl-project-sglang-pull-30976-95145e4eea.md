---
source_id: sglang-github-closed-issues-prs
title: 'fix: load the right mtp lm head quantization'
canonical_url: https://github.com/sgl-project/sglang/pull/30976
captured_at: '2026-07-15T23:40:28.355140+00:00'
content_hash: 95145e4eeaad8cc2dedd833a5a0acaa9d8378937cbc0f1e5a87887f50feabde6
---
# fix: load the right mtp lm head quantization

URL: https://github.com/sgl-project/sglang/pull/30976
State: closed
Labels: 
Closed at: 2026-07-15T19:12:04Z
Merged at: 2026-07-15T19:12:04Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation
fix loading quantized lm heads for nemotron models

## Modifications
share the main lm head

## Accuracy Tests
load older nemotron models (super v3 fp8) with mtp and run againt gsm8k to make sure they output valid output
load newest nemotron nano3.5 checkpoint with quantized lm_head and make sure it does not output garbage 

## Speed Tests and Profiling
no significant increase in model loading/inference time detect for either nano v3.5 or super v3.
## Checklist

- [X] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [X] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [X] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [X] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [X] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29397228266](https://github.com/sgl-project/sglang/actions/runs/29397228266)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29397227754](https://github.com/sgl-project/sglang/actions/runs/29397227754)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
