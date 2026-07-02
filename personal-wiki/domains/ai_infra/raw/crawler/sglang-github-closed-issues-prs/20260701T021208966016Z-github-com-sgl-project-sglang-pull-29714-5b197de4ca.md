---
source_id: sglang-github-closed-issues-prs
title: '[CI] Fix invalid JIT kernel suite registrations'
canonical_url: https://github.com/sgl-project/sglang/pull/29714
captured_at: '2026-07-01T02:12:08.966016+00:00'
content_hash: 5b197de4ca0f702351c984fe00fb21195d87cdc6818fe39dd06964094eea5627
---
# [CI] Fix invalid JIT kernel suite registrations

URL: https://github.com/sgl-project/sglang/pull/29714
State: closed
Labels: quant
Closed at: 2026-06-30T05:08:41Z
Merged at: 



<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

#29066 migrated kernel-suite registration to the `stage`/`runner_config` form (suite name = `{stage}-test-{runner_config}`), but a few JIT/benchmark/dcp tests added in parallel still use the old single-string `suite=` names. This makes `run_suite.py:validate_all_suites()` fail fast with "Tests registered to invalid suites" before any test runs, breaking every job that invokes `run_suite.py` (e.g. `extra-a-test-1-gpu-small-amd`).

## Modification

Migrate the remaining registrations to `stage`/`runner_config`:

- `base-b-kernel-unit-1-gpu-large` -> `stage=base-b-kernel-unit`, `runner_config=1-gpu-large`
- `base-b-kernel-unit-1-gpu-b200` -> `stage=base-b-kernel-unit`, `runner_config=4-gpu-b200`
- `base-b-kernel-unit-8-gpu-h200` -> `stage=base-b-kernel-unit`, `runner_config=8-gpu-h200`
- `base-b-kernel-benchmark-1-gpu-large` -> `stage=base-b-kernel-benchmark`, `runner_config=1-gpu-large`

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28421670248](https://github.com/sgl-project/sglang/actions/runs/28421670248)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28421670114](https://github.com/sgl-project/sglang/actions/runs/28421670114)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
