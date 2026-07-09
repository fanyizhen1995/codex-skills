---
source_id: sglang-github-closed-issues-prs
title: '[Tiny] Fix Import Error for Pure TP config with flashinfer_mxfp4'
canonical_url: https://github.com/sgl-project/sglang/pull/30426
captured_at: '2026-07-08T23:36:33.803691+00:00'
content_hash: b227e5971d17667bbeda0a75ccfe5bf81910a2e72ec8edc1dfed496a1de212f3
---
# [Tiny] Fix Import Error for Pure TP config with flashinfer_mxfp4

URL: https://github.com/sgl-project/sglang/pull/30426
State: closed
Labels: 
Closed at: 2026-07-08T01:17:53Z
Merged at: 2026-07-08T01:17:53Z

Pure-TP configs with --moe-runner-backend flashinfer_mxfp4 (a2a backend "none", e.g. DeepSeek-V4 NVFP4 on TP8 without expert parallelism) crash at model init:

  NotImplementedError: Runner backend MoeRunnerBackend.FLASHINFER_MXFP4
  requires a fused func for a2a backend none, but none is registered.

The (none, flashinfer_mxfp4) fused func is registered via @register_fused_func in flashinfer_cutlass.py, but that module — unlike deep_gemm/triton — is not imported by runner.py, so the decorator never runs and the pool lookup misses.

Fix: lazily import the flashinfer runner modules inside MoeRunner.__init__, just before the FusedOpPool lookup. Placed there (not at module top) to avoid a circular import through sglang.srt.layers.moe.__init__.

Verified: pure-TP8 + flashinfer_mxfp4 server now starts and reaches ready.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28906237551](https://github.com/sgl-project/sglang/actions/runs/28906237551)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28906237407](https://github.com/sgl-project/sglang/actions/runs/28906237407)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
