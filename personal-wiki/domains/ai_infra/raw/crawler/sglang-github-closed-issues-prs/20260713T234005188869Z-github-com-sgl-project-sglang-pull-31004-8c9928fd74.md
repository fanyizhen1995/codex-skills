---
source_id: sglang-github-closed-issues-prs
title: 'Fix: pp_proxy_tensors oversized at SCATTERED PP boundary breaks all_gather
  in CUDA graph capture'
canonical_url: https://github.com/sgl-project/sglang/pull/31004
captured_at: '2026-07-13T23:40:05.188869+00:00'
content_hash: 8c9928fd741ec0d32863e72e9e92acc467ff7605088f21ac3abd69ba2b672ab0
---
# Fix: pp_proxy_tensors oversized at SCATTERED PP boundary breaks all_gather in CUDA graph capture

URL: https://github.com/sgl-project/sglang/pull/31004
State: closed
Labels: 
Closed at: 2026-07-13T09:03:16Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Fix pp_proxy_tensors sizing for SCATTERED PP boundary in CUDA graph capture

When PP > 1 and DeepEP/moe_dense_tp_size=1 are used, the previous PP
stage's output is in ScatterMode.SCATTERED — each rank holds only
num_tokens / attn_tp_size rows, not num_tokens.

During CUDA graph capture, pp_proxy_tensors was unconditionally sliced
to num_tokens, causing the subsequent all_gather_into_tensor to fail:
  RuntimeError: output tensor size must be equal to world_size times
  input tensor size

The bug only manifests with all of: PP > 1, DeepEP backend, moe_dense_tp_size=1,
CUDA graph enabled, and attn_tp_size > 1.

original issue: https://gitcode.com/Ascend/slime-ascend/issues/17

## Modifications

Fix: slice pp_proxy_tensors to num_tokens // attn_tp_size when
require_attn_tp_gather is True, in both the decode CUDA graph capture
path (capture_prepare) and the eager warmup path (get_dummy_forward_batch).

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29235190808](https://github.com/sgl-project/sglang/actions/runs/29235190808)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29235190614](https://github.com/sgl-project/sglang/actions/runs/29235190614)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
