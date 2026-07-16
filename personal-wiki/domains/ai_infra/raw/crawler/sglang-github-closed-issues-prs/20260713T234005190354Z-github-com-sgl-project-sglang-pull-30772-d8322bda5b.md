---
source_id: sglang-github-closed-issues-prs
title: '[CI] Disable gated Llama-2 EAGLE spec tests to unblock Xeon CPU CI'
canonical_url: https://github.com/sgl-project/sglang/pull/30772
captured_at: '2026-07-13T23:40:05.190354+00:00'
content_hash: d8322bda5b2e25339ba44a8f073c42fa863c77669b9dea5053582a6aacbc912f
---
# [CI] Disable gated Llama-2 EAGLE spec tests to unblock Xeon CPU CI

URL: https://github.com/sgl-project/sglang/pull/30772
State: closed
Labels: intel, cpu, ci, run-ci
Closed at: 2026-07-13T06:24:06Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

The Xeon CPU CI (`base-b-test-cpu` on `xeon-gnr`) is currently failing caused by `test_spec_eagle_cpu.py` and `test_spec_eagle_topk_cpu.py` (added in #27862) launch `meta-llama/Llama-2-7b-chat-hf`, a gated Hugging Face checkpoint.

The runner's HF token has no Llama access and the model is not in its local cache, so the download 403s and the suite fails. #27862 was validated locally (the Xeon CI could not build at the time), where a cached copy masked this.

## Modifications

<!-- Detail the changes made in this pull request. -->

- Mark the `register_cpu_ci` registrations of both files `disabled=`.
 - `test_spec_eagle_parity_cpu.py` (EAGLE3, Llama-3.1-8B-Instruct) stays enabled for now.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29228569684](https://github.com/sgl-project/sglang/actions/runs/29228569684)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29228569510](https://github.com/sgl-project/sglang/actions/runs/29228569510)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
