---
source_id: sglang-github-closed-issues-prs
title: Fix Diffusion GT generation pipelines
canonical_url: https://github.com/sgl-project/sglang/pull/29926
captured_at: '2026-07-06T02:14:53.062347+00:00'
content_hash: cac2064e992ec39a949c58fd4965b1679715986a79c4b3090120cd581f81fde5
---
# Fix Diffusion GT generation pipelines

URL: https://github.com/sgl-project/sglang/pull/29926
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-05T08:43:50Z
Merged at: 2026-07-05T08:43:50Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

PR https://github.com/sgl-project/sglang/pull/28762 removed `collect_test_items` from `run_suite.py`, which broke `gen_diffusion_ci_outputs.py` used by the `diffusion-ci-gt-gen*.yml` workflows.

<!-- Describe the purpose and goals of this pull request. -->

## Modifications

This change adds `collect_test_items` directly to `gen_diffusion_ci_outputs.py` to restore the affected workflows.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28733884985](https://github.com/sgl-project/sglang/actions/runs/28733884985)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28733884948](https://github.com/sgl-project/sglang/actions/runs/28733884948)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
