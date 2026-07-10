---
source_id: sglang-github-closed-issues-prs
title: '[Kernel] Fix GPTQ shuffle Python wrapper'
canonical_url: https://github.com/sgl-project/sglang/pull/30515
captured_at: '2026-07-09T23:36:35.333007+00:00'
content_hash: c8d20b447a5ffb5288470688ebc062cdbf04bdf112a547f6dc91fb4b386c9a01
---
# [Kernel] Fix GPTQ shuffle Python wrapper

URL: https://github.com/sgl-project/sglang/pull/30515
State: closed
Labels: sgl-kernel
Closed at: 2026-07-09T09:17:17Z
Merged at: 

## Motivation

`sgl_kernel.gptq_shuffle()` is exported as the Python wrapper for the CUDA `sgl_kernel::gptq_shuffle` op and is used when processing GPTQ weights with act-order metadata. The wrapper currently calls `torch.torch.ops...`, which fails in Python before dispatching to the registered kernel.

## Modifications

- Route `gptq_shuffle()` through `torch.ops.sgl_kernel.gptq_shuffle`.
- Add a small CUDA smoke test that compares the public Python wrapper against the underlying `torch.ops` call, covering both empty and non-empty permutation inputs.

## Accuracy Tests

N/A. This only fixes the Python wrapper dispatch path for an existing kernel.

## Speed Tests and Profiling

N/A. No kernel implementation or launch configuration changes.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

Local checks:

```bash
python3 -m py_compile sgl-kernel/python/sgl_kernel/gemm.py sgl-kernel/tests/test_gptq_kernel.py
git diff --check HEAD~1..HEAD
```

I could not run the CUDA test locally because this environment does not have `torch`/CUDA installed.

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28933282343](https://github.com/sgl-project/sglang/actions/runs/28933282343)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28933282277](https://github.com/sgl-project/sglang/actions/runs/28933282277)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
