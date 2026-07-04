---
source_id: sglang-github-closed-issues-prs
title: '[NPU] bugfix for Base class add mamba_track_indices parameter'
canonical_url: https://github.com/sgl-project/sglang/pull/29999
captured_at: '2026-07-04T02:13:49.137089+00:00'
content_hash: 95cbd9989b51bf10704b8235370cb51a68daaf304a2910cd99a8246cb55e8f7d
---
# [NPU] bugfix for Base class add mamba_track_indices parameter

URL: https://github.com/sgl-project/sglang/pull/29999
State: closed
Labels: npu, run-ci
Closed at: 2026-07-03T07:10:41Z
Merged at: 2026-07-03T07:10:41Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation
bugfix for 2cases:
1. 
caz #29678 MambaAttnBackendBase class add mamba_track_indices, and affect its subclass ascendmamba--ascendgdnbackend.
sgl-sglang/python/sglang/srt/hardware_backend/npu/graph_runner/npu_graph_runner.py", line 103, in __init__
    super().__init__(
  File "/data/wzy/sgl-sglang/python/sglang/srt/model_executor/runner/decode_cuda_graph_runner.py", line 362, in __init__
    self.capture()
  File "/data/wzy/sgl-sglang/python/sglang/srt/model_executor/runner/decode_cuda_graph_runner.py", line 699, in capture
    self._capture_one_stream()
  File "/data/wzy/sgl-sglang/python/sglang/srt/model_executor/runner/decode_cuda_graph_runner.py", line 753, in _capture_one_stream
    self.capture_one_shape(bs, forward, stream_idx, variant_label)
  File "/data/wzy/sgl-sglang/python/sglang/srt/model_executor/runner/decode_cuda_graph_runner.py", line 784, in capture_one_shape
    attn_backend.init_forward_metadata_out_graph(forward_batch, in_capture=True)
  File "/data/wzy/sgl-sglang/python/sglang/srt/layers/attention/hybrid_linear_attn_backend.py", line 879, in init_forward_metadata_out_graph
    attn_backend.init_forward_metadata_out_graph(
  File "/data/wzy/sgl-sglang/python/sglang/srt/hardware_backend/npu/attention/ascend_gdn_backend.py", line 91, in init_forward_metadata_out_graph
    super().init_forward_metadata_out_graph(forward_batch, in_capture=in_capture)
  File "/data/wzy/sgl-sglang/python/sglang/srt/layers/attention/hybrid_linear_attn_backend.py", line 263, in init_forward_metadata_out_graph
    self.forward_metadata = self._replay_metadata(
                            ^^^^^^^^^^^^^^^^^^^^^^
TypeError: AscendMambaAttnBackendBase._replay_metadata() got an unexpected keyword argument 'mamba_track_indices'
2.
caz #29503 change the weight shape and gmm calls without considering deepep cases.
sgl-sglang/python/sglang/srt/layers/moe/fused_moe_triton/layer.py", line 1171, in run_moe_core
    return self.quant_method.apply(
           ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/data/wzy/sgl-sglang/python/sglang/srt/layers/quantization/unquant.py", line 453, in apply
    return self.forward(
           ^^^^^^^^^^^^^
  File "/data/wzy/sgl-sglang/python/sglang/srt/layers/utils/multi_platform.py", line 83, in forward
    return self._forward_method(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/data/wzy/sgl-sglang/python/sglang/srt/layers/quantization/unquant.py", line 663, in forward_npu
    return self._forward_npu_deepep(layer, dispatch_output)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/data/wzy/sgl-sglang/python/sglang/srt/layers/quantization/unquant.py", line 785, in _forward_npu_deepep
    hidden_states = npu_fused_moe_without_routing_weights_bf16(
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/data/wzy/sgl-sglang/python/sglang/srt/hardware_backend/npu/quantization/fused_moe_method_npu.py", line 285, in npu_fused_moe_without_routing_weights_bf16
    hidden_states = torch.ops.npu.npu_grouped_matmul(
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.15/lib/python3.11/site-packages/torch/_ops.py", line 1209, in __call__
    return self._op(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: npu_grouped_matmul:../third_party/op-plugin/op_plugin/ops/opapi/GroupedMatmulKernelNpuOpApi.cpp:322 NPU function error: call aclnnGroupedMatmulWeightNz failed, error code is 161002
[ERROR] 2026-07-03-02:49:31 (PID:594140, Device:2, RankID:-1) ERR00100 PTA call acl api failed.
[PID: 594140] 2026-07-03-02:49:31.770.240 AclNN_Parameter_Error(EZ1001): Dim 1 value of x[0] should be equal with dim 1 value of weight[0], but now is 2048 and 1024 respectively.
        TraceBack (most recent call last):
        K dim value of x and weight is not matched.
        Split m, single x, single weight, single y case failed.
        Invalid inputs!



<!-- Describe the purpose and goals of this pull request. -->

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28636892843](https://github.com/sgl-project/sglang/actions/runs/28636892843)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28636892780](https://github.com/sgl-project/sglang/actions/runs/28636892780)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
