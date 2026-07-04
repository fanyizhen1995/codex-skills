---
source_id: sglang-github-closed-issues-prs
title: '[XPU] Enable XPU graph support (decode full-graph + prefill tc_piecewise)'
canonical_url: https://github.com/sgl-project/sglang/pull/29053
captured_at: '2026-07-03T02:13:21.703429+00:00'
content_hash: 36bc5f93cffcf9488389c0c46a5ec44a8270bec0f9ca22da1cbc58d08b4c6300
---
# [XPU] Enable XPU graph support (decode full-graph + prefill tc_piecewise)

URL: https://github.com/sgl-project/sglang/pull/29053
State: closed
Labels: documentation, deepseek, intel, xpu, run-ci, piecewise-cuda-graph, run-ci-extra
Closed at: 2026-07-02T05:24:36Z
Merged at: 2026-07-02T05:24:35Z

## Motivation

This PR enables CUDA-graph-style capture/replay on Intel XPU, covering both the decode full-graph and the prefill tc_piecewise.
 
Co-authored with @huaiyuzh

## Modifications

* Decode full graph: new `XPUGraphRunner` (subclass of `DecodeCudaGraphRunner`) and `FullXPUGraphBackend`. Wired into `ModelRunner` and `resolve_decode_backend` (XPU accepts only `full/disabled` at current stage).
* Prefill `tc_piecewise`: `XPUPiecewiseBackend` mirrors `CUDAPiecewiseBackend` but captures into `torch.xpu.XPUGraph`; selected via `make_backend()`. `server_args` now keeps `tc_piecewise` for XPU prefill instead of force-disabling it.
* Attention metadata: `XPUAttentionBackend` gains the unified `init_forward_metadata_out_graph / init_forward_metadata_in_graph` graph entry points (decode-only), pre-allocated buffers reused across captures, optional pre-allocated `out=` for the FA kernel.
* Dynamo-capture fixes in `parallel_state`: route XPU `all_reduce / all_gather_into_tensor` through the existing opaque custom ops `inplace_all_reduce / reg_all_gather_into_tensor` so Dynamo does not decompose them into `_c10d_functional` + `wait_tensor`, which would break XPU graph capture at current stage. Semantics are unchanged (both still resolve to `torch.distributed.*`.
* Misc enablement: `weak_ref_tensor` for XPU (via sgl_kernel), register `_XpuDeviceProperties` as a Dynamo constant type, fake-op registration for `sgl_kernel::fwd/flash_mla_decode.
* New `test/registered/xpu/test_xpu_graph.py` runs `bench_one_batch` with decode full+ prefill tc_piecewise on Qwen2.5-1.5B.

## Accuracy Tests

The accuracy test results were no worse than those of the non-graph mode.

## Speed Tests and Profiling

XPU Graph achieved significant speedup in cases with substantial host overhead.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28507984860](https://github.com/sgl-project/sglang/actions/runs/28507984860)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28507984701](https://github.com/sgl-project/sglang/actions/runs/28507984701)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
