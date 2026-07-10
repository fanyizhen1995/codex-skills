---
source_id: sglang-github-closed-issues-prs
title: '[NPU][bugfix] Fix post_capture_active TypeError on NPU by adding param to
  NPUMHATokenToKVPool'
canonical_url: https://github.com/sgl-project/sglang/pull/30638
captured_at: '2026-07-09T23:36:35.331801+00:00'
content_hash: 5f46dba1b04523088ab2bf551c41d827cad35b0856e5732a841fc4cd4f2d9085
---
# [NPU][bugfix] Fix post_capture_active TypeError on NPU by adding param to NPUMHATokenToKVPool

URL: https://github.com/sgl-project/sglang/pull/30638
State: closed
Labels: npu
Closed at: 2026-07-09T09:39:53Z
Merged at: 2026-07-09T09:39:53Z

## Motivation

PR #30157 introduced post_capture_active to MHATokenToKVPool , but NPUMHATokenToKVPool does not accept this parameter. When SWAKVPool passes **kwargs (including post_capture_active ) to token_to_kv_pool_class , the NPU path raises TypeError: NPUMHATokenToKVPool.__init__() got an unexpected keyword argument 'post_capture_active' .

## Modifications

Added post_capture_active: bool = False parameter to NPUMHATokenToKVPool.__init__ and forwarded it to super().__init__() .

## Accuracy Tests

None. The fix only addresses a constructor interface mismatch; no model behavior is affected.

## Speed Tests and Profiling

None.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29008560975](https://github.com/sgl-project/sglang/actions/runs/29008560975)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29008560671](https://github.com/sgl-project/sglang/actions/runs/29008560671)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
