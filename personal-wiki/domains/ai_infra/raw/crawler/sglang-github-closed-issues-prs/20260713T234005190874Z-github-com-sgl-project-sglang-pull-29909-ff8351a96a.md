---
source_id: sglang-github-closed-issues-prs
title: '[Bugfix][NPU] Fix Hunyuan3 model where MoE''s routing_scaling_ratio is missing
  on NPU'
canonical_url: https://github.com/sgl-project/sglang/pull/29909
captured_at: '2026-07-13T23:40:05.190874+00:00'
content_hash: ff8351a96a2e02edce11673aa5f36cabb82e7cff7f644ddd55b7c6dc5df0f734
---
# [Bugfix][NPU] Fix Hunyuan3 model where MoE's routing_scaling_ratio is missing on NPU

URL: https://github.com/sgl-project/sglang/pull/29909
State: closed
Labels: run-ci
Closed at: 2026-07-13T06:48:41Z
Merged at: 2026-07-13T06:48:41Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation
```text
HY3-Preview Model was not able to reach official GPQA-D accuracy of 87.2 when running on NPU.
┌─────────────┬──────────────┬──────────┬──────────┬───────┬─────────┬─────────┐
│ Model       │ Dataset      │ Metric   │ Subset   │   Num │   Score │ Cat.0   │
├─────────────┼──────────────┼──────────┼──────────┼───────┼─────────┼─────────┤
│ Hy3-preview │ gpqa_diamond │ mean_acc │ default  │    40 │   0.175 │ default │
└─────────────┴──────────────┴──────────┴──────────┴───────┴─────────┴─────────┘
```
Hy3-preview  gpqa_diamond  40  925.395s  TTFT=21683ms  TPOT=39.88ms

**GPU Path**（`biased_grouped_topk_impl`，`layers/moe/topk.py`）：

```python
if renormalize:
    topk_weights_sum = topk_weights.sum(dim=-1, keepdim=True)
    topk_weights = topk_weights / topk_weights_sum  
    if apply_routed_scaling_factor_on_output:
        topk_weights *= routed_scaling_factor        # ← Applying routed_scaling_factor
```
But NPU lack this step, thus MoE's contribution to the final results were scaled down by ~2.8, and this accumulates in each MoE layer in Hunyuan-3.

In Hunyuan-3's config.json: 
```json
 "router_scaling_factor": 2.826,
```

## Modifications
In `python/sglang/srt/hardware_backend/npu/moe/topk.py`，function `fused_topk_npu`
```python
topk_weights = topk_weights.to(torch.float32)

# When renormalize=True, we pass routed_scaling_factor=1 to the op (no in-op
# scaling), so the op returns L1-normalized weights (sum=1).
# The GPU path (biased_topk_impl) then multiplies by routed_scaling_factor
# after renorm when apply_routed_scaling_factor_on_output=True.
# Mirror that behavior here.
if (
    renormalize
    and topk_config.apply_routed_scaling_factor_on_output
    and topk_config.routed_scaling_factor is not None
):
    topk_weights *= topk_config.routed_scaling_factor
```
Added this routed_scaling_factor

## Accuracy Tests
Final Result: After the fix, we can reach 0.8788 in GPQAD dataset, matching officials result.

```text
┌─────────────┬──────────────┬──────────┬──────────┬───────┬─────────┬─────────┐
│ Model       │ Dataset      │ Metric   │ Subset   │   Num │   Score │ Cat.0   │
├─────────────┼──────────────┼──────────┼──────────┼───────┼─────────┼─────────┤
│ Hy3-preview │ gpqa_diamond │ mean_acc │ default  │   198 │  0.8788 │ default │
└─────────────┴──────────────┴──────────┴──────────┴───────┴─────────┴─────────┘

Hy3-preview  gpqa_diamond  198  895.246s  TTFT=14435ms  TPOT=43.1ms  Thpt=22.71tok/s
```

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29218330412](https://github.com/sgl-project/sglang/actions/runs/29218330412)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29218330297](https://github.com/sgl-project/sglang/actions/runs/29218330297)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
