---
source_id: sglang-github-closed-issues-prs
title: '[diffusion][cache-dit] add dual-transformer Cache-DiT adapter specs'
canonical_url: https://github.com/sgl-project/sglang/pull/30150
captured_at: '2026-07-07T23:35:30.908700+00:00'
content_hash: 4afe2fd28c9717815e0185d84368c4ba4f6a36291eda4b76f8281b65b9c7a01e
---
# [diffusion][cache-dit] add dual-transformer Cache-DiT adapter specs

URL: https://github.com/sgl-project/sglang/pull/30150
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-07T15:10:53Z
Merged at: 2026-07-07T15:10:53Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->
Refactor dual-transformer Cache-DiT model metadata into declarative adapter specs, so adding future dual-transformer DiT pipelines does not require growing model-name based branches inside `enable_cache_on_dual_transformer`.

## Modifications

<!-- Detail the changes made in this pull request. -->
- Add `DualTransformerBlockAdapterSpec` for dual-transformer Cache-DiT metadata.
- Move Wan2.2 and Ideogram 4 dual-transformer BlockAdapter settings into `DUAL_TRANSFORMER_BLOCK_ADAPTER_SPECS`.
- Reuse the selected adapter spec inside `enable_cache_on_dual_transformer`.
- Update the Cache-DiT unit-test stub to include `ForwardPattern.Pattern_2`.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

This PR is a refactor and should not change model outputs.

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

No speed benchmark is included because this PR only refactors Cache-DiT adapter metadata and does not change Cache-DiT runtime behavior.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28846594975](https://github.com/sgl-project/sglang/actions/runs/28846594975)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28846594885](https://github.com/sgl-project/sglang/actions/runs/28846594885)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
