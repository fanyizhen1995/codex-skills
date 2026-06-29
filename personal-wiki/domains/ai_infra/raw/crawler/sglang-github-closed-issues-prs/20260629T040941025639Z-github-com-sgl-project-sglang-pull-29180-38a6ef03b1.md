---
source_id: sglang-github-closed-issues-prs
title: 'fix(deepep): fix DeepEP low-latency buffer capacity'
canonical_url: https://github.com/sgl-project/sglang/pull/29180
captured_at: '2026-06-29T04:09:41.025639+00:00'
content_hash: 38a6ef03b15ae716d1ac36b6c1a67a71a671d9221d056c14fe5343a72b19a60c
---
# fix(deepep): fix DeepEP low-latency buffer capacity

URL: https://github.com/sgl-project/sglang/pull/29180
State: closed
Labels: documentation, npu
Closed at: 2026-06-29T02:57:37Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

DeepEP low-latency dispatch receives the MoE input after attention-TP scatter. The configured per-rank token capacity should therefore be sized before scatter and converted to the actual DeepEP buffer capacity per attention-TP shard. Without this adjustment, runs with `attention_tp_size > 1` can allocate unnecessarily large DeepEP low-latency buffers. This is especially expensive for MTP workloads, where the low-latency buffer capacity is multiplied by the expanded decode-side token budget and can exceed **10GB** on some models.

## Modifications

<!-- Detail the changes made in this pull request. -->

- Import `get_attention_tp_size()` in the DeepEP token dispatcher.
- Treat `SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK` as the pre-scatter per-rank token capacity, then ceil-divide by attention TP size before passing the capacity to DeepEP.
- Keep behavior unchanged when `attention_tp_size == 1`.
- Add CPU unit coverage for attention-TP capacity scaling and the post-scatter DeepEP low-latency capacity limit.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

Not run locally per request. Model accuracy tests are not applicable because this change only adjusts DeepEP low-latency buffer capacity sizing; it does not change routing, kernels, or model numerics.

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

Not run locally per request. Speed benchmarking is not applicable as a runtime throughput comparison; the expected impact is lower DeepEP low-latency RDMA buffer allocation when `attention_tp_size > 1`, especially for MTP workloads. Runtime behavior is unchanged for `attention_tp_size == 1`.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28102255577](https://github.com/sgl-project/sglang/actions/runs/28102255577)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28102255420](https://github.com/sgl-project/sglang/actions/runs/28102255420)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
