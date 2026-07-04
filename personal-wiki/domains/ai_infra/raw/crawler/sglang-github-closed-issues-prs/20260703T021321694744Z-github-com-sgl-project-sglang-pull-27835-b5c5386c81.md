---
source_id: sglang-github-closed-issues-prs
title: '[bugfix][AMD] Disable aiter allreduce+RMSNorm fusion under DP attention /
  EP'
canonical_url: https://github.com/sgl-project/sglang/pull/27835
captured_at: '2026-07-03T02:13:21.694744+00:00'
content_hash: b5c5386c8182a563f94442c93f30c642fbbe315ed80a5eab2ae2e4eb2c9127a8
---
# [bugfix][AMD] Disable aiter allreduce+RMSNorm fusion under DP attention / EP

URL: https://github.com/sgl-project/sglang/pull/27835
State: closed
Labels: amd, deepseek, run-ci, bypass-fastfail
Closed at: 2026-07-02T22:31:25Z
Merged at: 2026-07-02T22:31:25Z

## Motivation

--enable-aiter-allreduce-fusion (the ROCm/aiter fused all-reduce + RMSNorm path) is only meaningful for the dense tensor-parallel path. The attention-side gate (apply_aiter_all_reduce_fusion) already excludes DP attention, but the MLP-side gate in LayerCommunicator.should_fuse_mlp_allreduce_with_next_layer was missing the matching guards.

As a result, enabling the flag together with DP attention and an expert-parallel A2A backend e.g. --enable-aiter-allreduce-fusion --enable-dp-attention --moe-a2a-backend mori --ep-size 8 sets _sglang_needs_allreduce_fusion and invokes the fused custom all-reduce during CUDA graph capture. This registers graph buffers that are incompatible with the EP/DP-attention layout and crashes startup:
```
Capture cuda graph failed: HIP error: an illegal memory access was encountered
  aiter/dist/device_communicators/custom_all_reduce.py: flush_graph_buffers
```
Under DP attention there is no dense TP all-reduce to fuse, and with an EP A2A backend the post-MoE reduction happens inside combine() rather than a TP all-reduce — so there is nothing for this op to fuse in those configs. The flag should be a safe no-op there instead of crashing.

## Modifications

`python/sglang/srt/layers/communicator.py` Add not is_dp_attention_enabled() and get_moe_a2a_backend().is_none() to the aiter branch of should_fuse_mlp_allreduce_with_next_layer, mirroring the guards already present in apply_aiter_all_reduce_fusion() and the flashinfer path. This makes the flag a no-op under DP attention or any EP A2A backend (mori/deepep/…) while leaving the supported dense-TP path unchanged.

`test/registered/layers/test_allreduce_fusion_gate.py` New CPU unit test (register_cpu_ci) covering the gate decision logic: fuses on dense TP; disabled under DP attention, under an EP backend, and in the combined DP-attn+EP config; plus pre-existing guards (opt-in flag off, last layer, TP=1). Module-level deps are stubbed and the method is invoked on a minimal fake instance, so no GPU/distributed init is needed.

## Accuracy Tests

No model-output behavior changes. 
Run using tests

## Speed Tests and Profiling

The change has no effect on the dense-TP fast path (where the fusion remains active) and no effect on EP throughput (where the fusion never legitimately ran).

Unit test results: 
```
collected 7 items
TestAiterAllreduceFusionGate::test_dense_tp_fuses PASSED                [ 14%]
TestAiterAllreduceFusionGate::test_dp_attention_and_ep_disables_fusion PASSED [ 28%]
TestAiterAllreduceFusionGate::test_dp_attention_disables_fusion PASSED  [ 42%]
TestAiterAllreduceFusionGate::test_ep_backend_disables_fusion PASSED    [ 57%]
TestAiterAllreduceFusionGate::test_flag_off_disables_fusion PASSED      [ 71%]
TestAiterAllreduceFusionGate::test_last_layer_disables_fusion PASSED    [ 85%]
TestAiterAllreduceFusionGate::test_tp1_disables_fusion PASSED           [100%]
======================== 7 passed, 5 warnings in 7.29s =========================
```

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28005732210](https://github.com/sgl-project/sglang/actions/runs/28005732210)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28067669262](https://github.com/sgl-project/sglang/actions/runs/28067669262)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
