---
source_id: sglang-github-closed-issues-prs
title: '[CPU] bypass scoring_func argument in topk for cpu device'
canonical_url: https://github.com/sgl-project/sglang/pull/31110
captured_at: '2026-07-14T23:40:21.670684+00:00'
content_hash: e3fb0d31e6ac64aebbe9b66a95757681dcddbb4a5d46cecf5a39864a8a0f0bbe
---
# [CPU] bypass scoring_func argument in topk for cpu device

URL: https://github.com/sgl-project/sglang/pull/31110
State: closed
Labels: intel, cpu, ci, run-ci
Closed at: 2026-07-14T13:48:23Z
Merged at: 2026-07-14T13:48:23Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

fix CI fail:

```
ERROR: test_latency_fp8_moe_model (__main__.TestIntelAMXAttnBackendQuant.test_latency_fp8_moe_model)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/opt/.venv/lib/python3.12/site-packages/sglang/srt/utils/common.py", line 3168, in retry
    return fn()
           ^^^^
  File "/opt/.venv/lib/python3.12/site-packages/sglang/test/test_utils.py", line 2216, in <lambda>
    lambda: super(CustomTestCase, self)._callTestMethod(method),
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/share/uv/python/cpython-3.12.13-linux-x86_64-gnu/lib/python3.12/unittest/case.py", line 589, in _callTestMethod
    if method() is not None:
       ^^^^^^^^
  File "/opt/.venv/lib/python3.12/site-packages/sglang/test/test_utils.py", line 2438, in wrapper
    prefill_latency, decode_throughput, decode_latency = run_bench_one_batch(
                                                         ^^^^^^^^^^^^^^^^^^^^
  File "/opt/.venv/lib/python3.12/site-packages/sglang/test/test_utils.py", line 1615, in run_bench_one_batch
    raise RuntimeError(
RuntimeError: Failed to parse benchmark output. prefill_latency=None, decode_throughput=None, decode_latency=None

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/opt/.venv/lib/python3.12/site-packages/sglang/test/test_utils.py", line 2215, in _callTestMethod
    retry(
  File "/opt/.venv/lib/python3.12/site-packages/sglang/srt/utils/common.py", line 3183, in retry
    raise Exception(f"retry() exceed maximum number of retries.")
Exception: retry() exceed maximum number of retries.

----------------------------------------------------------------------
```

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





























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29319026219](https://github.com/sgl-project/sglang/actions/runs/29319026219)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29319025981](https://github.com/sgl-project/sglang/actions/runs/29319025981)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
