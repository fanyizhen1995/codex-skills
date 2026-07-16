---
source_id: sglang-github-closed-issues-prs
title: '[NPU] [BUGFIX] Fix input parameters of swiglu_oai operator'
canonical_url: https://github.com/sgl-project/sglang/pull/30458
captured_at: '2026-07-14T23:40:21.682530+00:00'
content_hash: 32ae0fe8b8d50d362c4fd4a8212257a11cc901d2b94088dfc846efce2d4c878d
---
# [NPU] [BUGFIX] Fix input parameters of swiglu_oai operator

URL: https://github.com/sgl-project/sglang/pull/30458
State: closed
Labels: quant, run-ci
Closed at: 2026-07-14T06:16:25Z
Merged at: 2026-07-14T06:16:25Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Since pre-transposed storage is removed for layer.w13_weight, the swiglu_oai operator throws errors when fetching dimension information from layer.w13_weight. This PR fixes this bug.

## Modifications

<!-- Detail the changes made in this pull request. -->
Modify the swiglu_oai operator.


## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29148126820](https://github.com/sgl-project/sglang/actions/runs/29148126820)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29148126770](https://github.com/sgl-project/sglang/actions/runs/29148126770)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
