---
source_id: sglang-github-closed-issues-prs
title: 'feat: Support HiCache for MiMo-V2 models (2/N)'
canonical_url: https://github.com/sgl-project/sglang/pull/27629
captured_at: '2026-07-10T23:37:20.324195+00:00'
content_hash: 89e83d76eecea94b9e8d40171babab5b2b9946a045e077ea24cbabf2e6153368
---
# feat: Support HiCache for MiMo-V2 models (2/N)

URL: https://github.com/sgl-project/sglang/pull/27629
State: closed
Labels: sgl-kernel, run-ci, run-ci-extra
Closed at: 2026-06-12T06:39:45Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

Adds asymmetric K/V (different head_dim for K vs V) support to the
HiCache KV transfer CUDA kernel path used by MiMo-V2 models, and
introduces targeted regression tests to validate both symmetric
and asymmetric configurations.

This is the sgl-kernel side of MiMo-V2 HiCache enablement; the host pool /
server-args side is in #27378.

## Modifications

<!-- Detail the changes made in this pull request. -->

- Extend the core transfer kernel/launcher to compute V-specific `item_size` and `layout_dim` independently from K when head dims differ.
- Auto-derive `k_head_dim`/`v_head_dim` in the affected public entrypoints (`transfer_kv_per_layer_pf_lf`, `transfer_kv_all_layer_lf_pf`) without changing their ABI.
- Add new pytest coverage for symmetric (128/128) and MiMo-V2-like asymmetric (192/128) transfers.


## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #27185387685](https://github.com/sgl-project/sglang/actions/runs/27185387685)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27185387613](https://github.com/sgl-project/sglang/actions/runs/27185387613)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
