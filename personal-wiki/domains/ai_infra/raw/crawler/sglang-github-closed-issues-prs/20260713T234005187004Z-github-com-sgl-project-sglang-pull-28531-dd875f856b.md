---
source_id: sglang-github-closed-issues-prs
title: '[Intel GPU] Guard tvm_ffi import in dsv4 online mtp module under TYPE_CHECKING
  to fix import error on XPU'
canonical_url: https://github.com/sgl-project/sglang/pull/28531
captured_at: '2026-07-13T23:40:05.187004+00:00'
content_hash: dd875f856b2918bf32d1d24db0e3da7a6e1e4824d55f3d56024809fe115d2eca
---
# [Intel GPU] Guard tvm_ffi import in dsv4 online mtp module under TYPE_CHECKING to fix import error on XPU

URL: https://github.com/sgl-project/sglang/pull/28531
State: closed
Labels: intel, run-ci, jit-kernel, run-ci-extra
Closed at: 2026-06-22T05:56:21Z
Merged at: 2026-06-22T05:56:21Z

due to https://github.com/sgl-project/sglang/pull/26471

XPU doesn't support apache-tvm-ffi yet so we get below error
```
python/sglang/jit_kernel/dsv4/online_c128_mtp.py", line 7, in <module>
    from tvm_ffi.module import Module
ModuleNotFoundError: No module named 'tvm_ffi`
```
<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

## Modifications

<!-- Detail the changes made in this pull request. -->

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #27733404220](https://github.com/sgl-project/sglang/actions/runs/27733404220)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #27733404125](https://github.com/sgl-project/sglang/actions/runs/27733404125)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
