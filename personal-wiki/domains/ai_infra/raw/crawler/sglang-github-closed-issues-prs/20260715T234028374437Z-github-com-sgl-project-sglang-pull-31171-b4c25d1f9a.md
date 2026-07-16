---
source_id: sglang-github-closed-issues-prs
title: '[CPU] add fused input proj for qwen3.5'
canonical_url: https://github.com/sgl-project/sglang/pull/31171
captured_at: '2026-07-15T23:40:28.374437+00:00'
content_hash: b4c25d1f9a92a11b94711328a1403b045c87ff0e516bcb02c048f405b37eff20
---
# [CPU] add fused input proj for qwen3.5

URL: https://github.com/sgl-project/sglang/pull/31171
State: closed
Labels: sgl-kernel, intel, cpu, run-ci
Closed at: 2026-07-15T07:06:25Z
Merged at: 2026-07-15T07:06:25Z



## Motivation

Adds `fused_input_proj_cpu` to compute in_proj_qkvz and in_proj_ba in one CPU kernel.

## Modifications

- Adds `fused_input_proj_cpu` to compute in_proj_qkvz and in_proj_ba in one CPU kernel.
- Registers the new op in the CPU torch extension and torch.compile fake registry.
- Wires Qwen3.5 CPU bf16 AMX/no-bias path to use the fused op.
- Simplifies related CPU Qwen3 kernels and updates tests to pytest style.

## Accuracy Tests

python -m pytest test_qwen3.py -vv -s



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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29384696381](https://github.com/sgl-project/sglang/actions/runs/29384696381)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29384696319](https://github.com/sgl-project/sglang/actions/runs/29384696319)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
