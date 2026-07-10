---
source_id: sglang-github-closed-issues-prs
title: 'fix(mtp): avoid mtp perf regression in deepseek when enable eplb'
canonical_url: https://github.com/sgl-project/sglang/pull/28982
captured_at: '2026-07-09T23:36:35.324215+00:00'
content_hash: b6bb4d83f46c062303afe31829541a50f93a8ab4ef7a8f2de69e652dfa44f7c0
---
# fix(mtp): avoid mtp perf regression in deepseek when enable eplb

URL: https://github.com/sgl-project/sglang/pull/28982
State: closed
Labels: deepseek, run-ci, bypass-fastfail
Closed at: 2026-07-09T18:29:07Z
Merged at: 2026-07-09T18:29:07Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation
When EPLB and MTP are enabled in DeepSeek, the draft model reusing the target model's dispatch info causes a degradation in accept rate. We introduce the is_nextn flag to fix this issue. This approach is consistent with the implementation in Qwen3 MoE (see _forward_deepep in Qwen2MoeSparseMoeBlock).

<!-- Describe the purpose and goals of this pull request. -->

## Modifications
In deepseek_v2.py, we now leverage the is_nextn flag to differentiate between the draft model and the target model during execution, replacing the previous ambiguous check.
<!-- Detail the changes made in this pull request. -->

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28993965296](https://github.com/sgl-project/sglang/actions/runs/28993965296)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28993965172](https://github.com/sgl-project/sglang/actions/runs/28993965172)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
