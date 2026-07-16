---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Update qwen3.5 cookbook'
canonical_url: https://github.com/sgl-project/sglang/pull/31258
captured_at: '2026-07-15T23:40:28.384062+00:00'
content_hash: 0ab242f960c614babf549bde9a45e559ae9181321c35837aea1278e7b646daae
---
# [AMD] Update qwen3.5 cookbook

URL: https://github.com/sgl-project/sglang/pull/31258
State: closed
Labels: documentation
Closed at: 2026-07-15T02:59:13Z
Merged at: 2026-07-15T02:59:13Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

Update amd qwen 3.5 command and docs.
Sync with inferenceX script.
InferenceX PR: https://github.com/SemiAnalysisAI/InferenceX/pull/2201
cc @yichiche 

## Modifications

<!-- Detail the changes made in this pull request. -->

Add `AITER_FLYDSL_FORCE=1 SGLANG_MAMBA_SSM_DTYPE=bfloat16 `.
Check with `mint`.
<img width="647" height="268" alt="image" src="https://github.com/user-attachments/assets/8f64a867-7776-4633-bfd8-43a60c7b4bff" />
<img width="668" height="177" alt="image" src="https://github.com/user-attachments/assets/7cab32ce-108e-4029-a07a-3a861d874431" />

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
