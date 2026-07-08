---
source_id: sglang-github-closed-issues-prs
title: '[NPU] Fix DeepEP unquant MoE weight layout'
canonical_url: https://github.com/sgl-project/sglang/pull/30085
captured_at: '2026-07-05T02:14:10.262462+00:00'
content_hash: a94d45b1d81a6fc3b3c27315adfb80f64f450b7824bd5dacd9970bab120ef30f
---
# [NPU] Fix DeepEP unquant MoE weight layout

URL: https://github.com/sgl-project/sglang/pull/30085
State: closed
Labels: npu
Closed at: 2026-07-04T02:24:34Z
Merged at: 

## Motivation

Fix GLM-5.2 startup failure on Ascend NPU with DeepEP + BF16 MoE.

After recent NPU MoE weight loading changes, the normal NPU MoE path transposes expert weights before calling `npu_grouped_matmul`, but the DeepEP BF16 path still passed `layer.w13_weight` and `layer.w2_weight` directly. This can trigger a grouped matmul K-dimension mismatch, e.g. `x` has K=6144 while `weight` has K=4096.

## Modifications

Update `npu_fused_moe_without_routing_weights_bf16` to transpose BF16 MoE expert weights before passing them to `torch.ops.npu.npu_grouped_matmul`.

This makes the DeepEP BF16 path consistent with the normal NPU MoE forward path.

## Accuracy Tests

Not run in this environment.

This change fixes a runtime shape mismatch during GLM-5.2 startup on Ascend NPU. Please see the reported failure:
`Dim 1 value of x[0] should be equal with dim 1 value of weight[0], but now is 6144 and 4096 respectively.`

## Speed Tests and Profiling

Not run.

The change only applies the expected weight layout transpose for the BF16 DeepEP NPU MoE path.

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to the [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28691984116](https://github.com/sgl-project/sglang/actions/runs/28691984116)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28691984030](https://github.com/sgl-project/sglang/actions/runs/28691984030)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
