---
source_id: sglang-github-closed-issues-prs
title: '[docs] Port cookbook skills for docs_new'
canonical_url: https://github.com/sgl-project/sglang/pull/24114
captured_at: '2026-07-08T23:36:33.801291+00:00'
content_hash: abe5fe1564f17e2a556c2318a84d42c0a35e1db6a587f4b129e929d18ef8a835
---
# [docs] Port cookbook skills for docs_new

URL: https://github.com/sgl-project/sglang/pull/24114
State: closed
Labels: documentation
Closed at: 2026-07-08T02:47:07Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Port the original cookbook skills from sgl-project/sgl-cookbook and adapt them to the Mintlify-based cookbook layout in docs_new/.

- cookbook-add-model: interactive workflow for adding a new model — MDX page under docs_new/cookbook/autoregressive/<Vendor>/, JSX deployment snippet under docs_new/src/snippets/autoregressive/, navigation entry in docs_new/docs.json, and vendor card in cookbook/autoregressive/intro.mdx.
- cookbook-review-pr: PR-review checklist tuned to the docs_new layout (file hygiene, frontmatter, snippet quality, port-30000 consistency, doc-vs-snippet parity, mint validate, etc).

Both skills drop the data/models YAML pipeline, sidebars.js, and compile_models.py references from the old Docusaurus layout — those don't exist in docs_new/.

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
