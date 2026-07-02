---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Split qwen3.5 triton DCP test into its own nightly job'
canonical_url: https://github.com/sgl-project/sglang/pull/29409
captured_at: '2026-07-02T02:12:27.264364+00:00'
content_hash: 24a7ff26a84989fc82354eeb5b6258d80c0e8d13fa687f05ab005e0f4a8fae21
---
# [AMD] Split qwen3.5 triton DCP test into its own nightly job

URL: https://github.com/sgl-project/sglang/pull/29409
State: closed
Labels: amd
Closed at: 2026-07-01T07:39:40Z
Merged at: 2026-07-01T07:39:40Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation
The AMD nightly job `nightly-8-gpu-mi35x-qwen35` keeps timing out.
The suite `nightly-amd-accuracy-8-gpu-mi35x-qwen35` contained **two** test files:
| Test file | est_time |
| --- | --- |
| `test_qwen35_eval_mi35x.py` | 3600s |
| `test_qwen3p5_triton_dcp.py` | 4800s |
They run sequentially within a single step whose `timeout-minutes: 120` (7200s),
but the combined estimate is ~8400s, so the job exceeds the timeout.
## Modifications
- Move `test_qwen3p5_triton_dcp.py` to a dedicated suite
  `nightly-amd-accuracy-8-gpu-mi35x-qwen35-triton-dcp`.
- Add a standalone job `nightly-8-gpu-mi35x-qwen35-triton-dcp` in
  `nightly-test-amd.yml` (and `...-rocm720` in `nightly-test-amd-rocm720.yml`),
  each with its own 120-minute budget.
- Register the new jobs in the `job_select` dropdown and the `check-all-jobs`
  `needs` list of both workflows.
After the split, `nightly-8-gpu-mi35x-qwen35` runs only the lm-eval test
(~3600s) and the triton DCP test (~4800s) runs in its own job.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28428530158](https://github.com/sgl-project/sglang/actions/runs/28428530158)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28428530034](https://github.com/sgl-project/sglang/actions/runs/28428530034)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
