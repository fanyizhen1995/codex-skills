---
source_id: sglang-github-closed-issues-prs
title: Skip custom all-reduce v2 CUDA graph capture with torch memory saver.
canonical_url: https://github.com/sgl-project/sglang/pull/27948
captured_at: '2026-07-01T02:12:08.954456+00:00'
content_hash: 746f7154ad42e38373d220d860b7d9675f384dfa380c95f896bad11c5b9c8dab
---
# Skip custom all-reduce v2 CUDA graph capture with torch memory saver.

URL: https://github.com/sgl-project/sglang/pull/27948
State: closed
Labels: jit-kernel
Closed at: 2026-06-30T21:53:30Z
Merged at: 2026-06-30T21:53:30Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Similiar to https://github.com/sgl-project/sglang/pull/19162.

### Root Cause
1. `--colocate` enables `torch_memory_saver` for the rollout engine.
2. `custom_all_reduce_v2.py` captured custom all-reduce without using the unregistered graph-input path.
3. The kernel expected runtime-allocated IPC handles, but TMS hooked them to driver IPC handles during capture.
4. `custom_all_reduce.cuh` then received invalid graph input metadata and failed at runtime check, causing 
```
Exception: Capture cuda graph failed: Runtime check failed at /sgl-workspace/sglang/python/sglang/jit_kernel/include/sgl_kernel/distributed/custom_all_reduce.cuh:37: CUDA error: invalid argument
```

## Modifications

When `SGLANG_MEMORY_SAVER_CUDA_GRAPH=true`, custom all-reduce v2 now treats graph inputs as unregistered and routes pull kernels through the internal-buffer path instead of registering captured IPC addresses.


## Accuracy Tests

- 8-GPU Miles Megatron colocate passed step0 end-to-end, with v2 init and. CUDA graph capture.


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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28200478631](https://github.com/sgl-project/sglang/actions/runs/28200478631)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28200478545](https://github.com/sgl-project/sglang/actions/runs/28200478545)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
