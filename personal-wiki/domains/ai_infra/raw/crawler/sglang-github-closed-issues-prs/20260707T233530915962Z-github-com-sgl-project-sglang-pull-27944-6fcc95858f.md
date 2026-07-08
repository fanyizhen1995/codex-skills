---
source_id: sglang-github-closed-issues-prs
title: Support MiniMax-M3
canonical_url: https://github.com/sgl-project/sglang/pull/27944
captured_at: '2026-07-07T23:35:30.915962+00:00'
content_hash: 6fcc95858f31900ff035e76311a01edb97e106579ee5f4489a9e0991dd6120f3
---
# Support MiniMax-M3

URL: https://github.com/sgl-project/sglang/pull/27944
State: closed
Labels: quant, amd, hicache, run-ci, jit-kernel, bypass-fastfail, run-ci-extra
Closed at: 2026-07-07T06:24:15Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

> **Note: This PR is kept as a reference only.**
>
> The MiniMax-M3 landing effort has been split into smaller, separately-reviewed PRs to ease review and unblock CI. This branch (`minimax-m3-upstream`) aggregates the full M3 work end-to-end (model + sparse HiCache + MTP + AR-fusion + cookbook e2e) and is **not intended to be merged as-is**. New contributions should target the split PRs instead; this PR exists to cross-reference the complete picture and the cumulative e2e/precision verification done here.
>
> See the linked PRs for the individual landing pieces.

## Modifications

<!-- Detail the changes made in this pull request. -->

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to the [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to the [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28222107735](https://github.com/sgl-project/sglang/actions/runs/28222107735)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28222107619](https://github.com/sgl-project/sglang/actions/runs/28222107619)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
