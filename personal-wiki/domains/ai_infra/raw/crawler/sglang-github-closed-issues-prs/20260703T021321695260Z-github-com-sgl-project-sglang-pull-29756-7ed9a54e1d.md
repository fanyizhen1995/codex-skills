---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Fix MiniMax M3 state transfer in Mori PD'
canonical_url: https://github.com/sgl-project/sglang/pull/29756
captured_at: '2026-07-03T02:13:21.695260+00:00'
content_hash: 7ed9a54e1d50b4853b23c244effa72f2310edadbc9b54e06c0aae3851231494f
---
# [AMD] Fix MiniMax M3 state transfer in Mori PD

URL: https://github.com/sgl-project/sglang/pull/29756
State: closed
Labels: amd, run-ci
Closed at: 2026-07-02T22:02:11Z
Merged at: 2026-07-02T22:02:11Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation
#28714 introduced StateType.MINIMAX_INDEX_K for MiniMax-M3 sparse attention state transfer and wired it through Mooncake/NIXL. Mori's state dispatch allowlist still rejected the same state type, causing PD state transfer to fail with:

  unknown state_type=minimax_index_k

<!-- Describe the purpose and goals of this pull request. -->

## Modifications
MiniMax index-K state is a flat state component and can use Mori's existing SWA/DSA flat state transfer path for the same-TP 1P1D case, so extend the Mori allowlist to dispatch minimax_index_k there as well.
<!-- Detail the changes made in this pull request. -->

## Accuracy Tests

- Rebased #28715 on latest main, then applied this one-line Mori patch.
- Ran MiniMax-M3 MXFP8 1P1D on g05/g06 with Mori RDMA devices rdma0-7.
- 17*23 smoke passed.
- GSM8K-style 10-question smoke passed, 10/10.
- No unknown state_type=minimax_index_k or PD state transfer error in logs.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28503608002](https://github.com/sgl-project/sglang/actions/runs/28503608002)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28503607735](https://github.com/sgl-project/sglang/actions/runs/28503607735)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
