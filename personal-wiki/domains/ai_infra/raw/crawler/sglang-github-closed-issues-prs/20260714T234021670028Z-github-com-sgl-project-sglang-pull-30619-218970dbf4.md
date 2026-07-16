---
source_id: sglang-github-closed-issues-prs
title: '[NPU] Fix CPU device for node topology probe'
canonical_url: https://github.com/sgl-project/sglang/pull/30619
captured_at: '2026-07-14T23:40:21.670028+00:00'
content_hash: 218970dbf43b54bb0f5f2639f5132ff4574b607bbc191cd41f290e067199b1db
---
# [NPU] Fix CPU device for node topology probe

URL: https://github.com/sgl-project/sglang/pull/30619
State: closed
Labels: run-ci
Closed at: 2026-07-14T14:17:55Z
Merged at: 2026-07-14T14:17:55Z


## Motivation

Fix an NPU multi-node `LogitsProcessor` initialization failure caused by the node topology probe creating its communication tensor on the current default device instead of CPU.

When SGLang runs under an NPU device context, the following tensor may be created on NPU:

```python
is_in_the_same_node = torch.tensor([0] * world_size, dtype=torch.int32)
```

However, `in_the_same_node_as()` performs `all_reduce` through a CPU process group. This device/backend mismatch results in:

```text
RuntimeError: No backend type associated with device type npu
```

## Modifications

- Explicitly create the node topology probe tensor on CPU by specifying `device="cpu"`.
- Ensure the tensor device matches the CPU process group used by `in_the_same_node_as()`.
- Keep the existing `MultimemAllGatherer` initialization and platform behavior unchanged.

## Accuracy Tests

This change does not affect model computation or logits values. It only fixes the device placement of an internal node topology probe tensor.

## Speed Tests and Profiling

The change only adds an explicit device argument during initialization and is not expected to affect inference performance.

## Checklist

- [ ] Format your code according to the [[Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit)](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [[Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests)](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [[Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations)](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [[Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy)](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [[Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed)](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [[guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance)](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [[PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process)](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [[CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS)](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [[comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests)](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.

































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29303206674](https://github.com/sgl-project/sglang/actions/runs/29303206674)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29303206619](https://github.com/sgl-project/sglang/actions/runs/29303206619)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
