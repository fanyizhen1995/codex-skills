---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Fix DeepSeekV4 server cutlass error'
canonical_url: https://github.com/sgl-project/sglang/pull/30374
captured_at: '2026-07-07T23:35:30.902859+00:00'
content_hash: 9d31fb1b427d87c5d53abc62094083a990fc40d3ff76aaad54e83e646aba76c0
---
# [AMD] Fix DeepSeekV4 server cutlass error

URL: https://github.com/sgl-project/sglang/pull/30374
State: closed
Labels: run-ci, jit-kernel
Closed at: 2026-07-07T21:43:06Z
Merged at: 2026-07-07T21:43:06Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

PR #25220 introduced a top-level import of the CuTeDSL MQA logits module, which depends on NVIDIA-only cutlass packages. 

On AMD/ROCm environments without cutlass, this import fails during DSV4 model registration and prevents the server from starting, even though the CuTeDSL backend is not used.
<img width="1627" height="499" alt="image" src="https://github.com/user-attachments/assets/210f5e7b-1b6f-454f-b046-4fa2f7846316" />

## Modifications

Guard the CuTeDSL imports behind `not is_hip()`. On non-ROCm platforms, preserve the original eager import behavior so NVIDIA/CuTeDSL logic remains unchanged.

## Accuracy Tests

root@smci355-ccs-aus-n12-13:/sgl-workspace/sglang# python3 /sgl-workspace/sglang/benchmark/gsm8k/bench_sglang.py --port 8000 --num-questions 1319

100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 1319/1319 [01:08<00:00, 19.29it/s]
Accuracy: 0.948
Invalid: 0.000
Latency: 68.365 s
Output throughput: 1728.667 token/s

## Speed Tests and Profiling
This PR has almost no impact on performance.
TP8 DP8, 8k/1k, concurrency = 256, num prompts = 4 × concurrency | Total token throughput (tok/s) | Mean TTFT (ms) | Mean TPOT (ms)
-- | -- | -- | --
Main branch | failed | failed | failed 
This PR | 34904.71 | 6871.52 | 57.17

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28877915192](https://github.com/sgl-project/sglang/actions/runs/28877915192)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28877913869](https://github.com/sgl-project/sglang/actions/runs/28877913869)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
