---
source_id: sglang-github-closed-issues-prs
title: Move breakable CUDA graph back into model_executor/runner_backend_utils
canonical_url: https://github.com/sgl-project/sglang/pull/30586
captured_at: '2026-07-09T23:36:35.339290+00:00'
content_hash: e81df815eee6f3a566543b2809b043fed5a0f949730e92b334efd41dabbe6959
---
# Move breakable CUDA graph back into model_executor/runner_backend_utils

URL: https://github.com/sgl-project/sglang/pull/30586
State: closed
Labels: run-ci, diffusion, bypass-fastfail
Closed at: 2026-07-09T06:19:17Z
Merged at: 2026-07-09T06:19:17Z

Reverts the package relocation from sgl-project/sglang#27436, which hoisted the BCG core out to sglang.srt.breakable_cuda_graph. The full implementation now lives back at
sglang.srt.model_executor.runner_backend_utils.breakable_cuda_graph and the top-level package is removed; all importers are repointed.

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

## Modifications

<!-- Detail the changes made in this pull request. -->

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28991132395](https://github.com/sgl-project/sglang/actions/runs/28991132395)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28991132207](https://github.com/sgl-project/sglang/actions/runs/28991132207)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
