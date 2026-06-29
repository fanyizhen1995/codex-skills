---
source_id: sglang-github-closed-issues-prs
title: '[NPU][Bugfix] Fix a ModelSlim loading failure'
canonical_url: https://github.com/sgl-project/sglang/pull/29029
captured_at: '2026-06-29T04:09:41.027590+00:00'
content_hash: 7a7af86237912b85af5c20ea24c5f46aae5101ba7e8d735185d546cf1a8c0977
---
# [NPU][Bugfix] Fix a ModelSlim loading failure

URL: https://github.com/sgl-project/sglang/pull/29029
State: closed
Labels: run-ci
Closed at: 2026-06-29T01:53:02Z
Merged at: 2026-06-29T01:53:02Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Fix a ModelSlim loading failure on Ascend NPU for GLM-5.2 / DSA-style models.

Previously, `ModelSlimConfig.get_linear_scheme()` returned `None` for these layers, but `get_quant_method()` still returned `ModelSlimLinearMethod`. This caused model initialization to fail when `ModelSlimLinearMethod.create_weights()` attempted to call `layer.scheme.create_weights()`:


```text
AttributeError: 'NoneType' object has no attribute 'create_weights'
```

## Modifications

If `get_linear_scheme()` returns `None`, `get_quant_method()` now returns `UnquantizedLinearMethod()` instead of `ModelSlimLinearMethod`. This keeps `get_linear_scheme()` responsible only for resolving ModelSlim schemes, while unsupported or unquantized linear layers use the standard unquantized linear path.

## Accuracy Tests

This change only affects ModelSlim initialization fallback for linear layers without a supported quantization scheme. Quantized layers with valid ModelSlim scheme entries continue to use the existing ModelSlim path.

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->
The change may make unsupported/unquantized linear layers use the standard unquantized linear path, but does not change kernels or execution paths for layers with valid ModelSlim quantization schemes.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28018163843](https://github.com/sgl-project/sglang/actions/runs/28018163843)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28018165011](https://github.com/sgl-project/sglang/actions/runs/28018165011)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
