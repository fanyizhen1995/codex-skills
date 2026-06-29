---
source_id: sglang-github-closed-issues-prs
title: '[CPU] enable fused_sigmoid_mul on CPU device'
canonical_url: https://github.com/sgl-project/sglang/pull/29378
captured_at: '2026-06-29T04:09:41.028804+00:00'
content_hash: ba0a56bb060116144650c0c9b5e95b5f220da1bccbddfa10e2b6f384056e5053
---
# [CPU] enable fused_sigmoid_mul on CPU device

URL: https://github.com/sgl-project/sglang/pull/29378
State: closed
Labels: sgl-kernel, intel, cpu, run-ci
Closed at: 2026-06-29T01:38:04Z
Merged at: 2026-06-29T01:38:04Z

## Motivation
Add a CPU kernel for attention output gating used by Qwen3.5: attn_output * sigmoid(gate).

Previously, the CPU path fell back to PyTorch eager (`reshape` + `sigmoid` + `mul_`), while GPU used a fused Triton kernel. This This PR adds `fused_sigmoid_mul_cpu` and wires it into Qwen3.5 on CPU.

## Modifications

* Kernel (sgl-kernel/csrc/cpu/activation.cpp)
* Registers torch.ops.sgl_kernel.fused_sigmoid_mul_cpu in torch_extension_cpu.cpp
* Qwen3.5 CPU path uses the fused op instead of eager fallback (NPU still uses its own path)

## Accuracy Tests

`python test/registered/cpu/test_activation.py`




## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28217529304](https://github.com/sgl-project/sglang/actions/runs/28217529304)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28217538303](https://github.com/sgl-project/sglang/actions/runs/28217538303)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
