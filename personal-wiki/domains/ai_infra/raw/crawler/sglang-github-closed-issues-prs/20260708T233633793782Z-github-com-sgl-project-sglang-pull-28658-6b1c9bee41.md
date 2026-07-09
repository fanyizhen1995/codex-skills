---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Fuse shared-expert sigmoid + bf16->fp32 cast into the MoE append kernel
  (3 kernels -> 1)'
canonical_url: https://github.com/sgl-project/sglang/pull/28658
captured_at: '2026-07-08T23:36:33.793782+00:00'
content_hash: 6b1c9bee41728fa804b5f03eb1568a248165f51739368e850f27796a327a7f60
---
# [AMD] Fuse shared-expert sigmoid + bf16->fp32 cast into the MoE append kernel (3 kernels -> 1)

URL: https://github.com/sgl-project/sglang/pull/28658
State: closed
Labels: run-ci
Closed at: 2026-07-08T09:34:21Z
Merged at: 2026-07-08T09:34:21Z

## Motivation

On the AITER shared-expert-fusion path (`Qwen2MoeSparseMoeBlock._append_shared_to_topk_output`), preparing the fused shared-expert routing weight launched **three** GPU kernels per MoE layer per decode step:

1. `sigmoid_kernel_cuda` — `w = F.sigmoid(shared_logits)` in `_get_shared_expert_weights` (~5.5 us)
2. `bfloat16tofloat32_copy_kernel_cuda` — `shared_weights.to(topk_weights.dtype)` inside the append wrapper (~4.5 us)
3. `_fused_append_shared_experts_with_weights_kernel` — the append itself (~4.2 us)

These are tiny, bandwidth/launch-bound elementwise ops on small tensors. The sigmoid and the bf16→fp32 cast are pure glue feeding the append kernel, so they can be folded into the append kernel's prologue. This collapses 3 kernels into 1 and removes two global round-trips per MoE layer.

## Modifications

- `python/sglang/srt/layers/moe/moe_runner/triton_utils/fused_moe_triton_kernels.py`
  - `_fused_append_shared_experts_with_weights_kernel`: added a `scale` runtime arg and an `APPLY_SIGMOID: tl.constexpr`. When set, the shared-weight load computes `sigmoid(logits.to(fp32)) * scale` in-register, emitting fp32 straight into the output.
  - `fused_append_shared_experts_with_weights(...)`: added `apply_sigmoid=False, scale=1.0`. When `apply_sigmoid=True`, raw bf16 gate logits are streamed in directly (host-side `.to(fp32)` cast skipped); the legacy path is byte-for-byte unchanged when the flag is off.
- `python/sglang/srt/models/qwen2_moe.py`
  - `_get_shared_expert_weights`: returns the **raw** gate logits plus a `1/ep_size` scale instead of `sigmoid(logits) / ep_size` (the activation and scale are now applied inside the kernel).
  - `_append_shared_to_topk_output`: passes `apply_sigmoid=True, scale=...` to the append wrapper.

Net effect: `sigmoid` + bf16→fp32 cast are fused into the existing append kernel — **3 kernels → 1**, ~10 us/layer of glue removed, at ~0 added cost to the append kernel.

## Accuracy Tests

GSM8K (200 questions, parallel 2000, greedy), Qwen3.5-397B-A17B-MXFP4, tp=2, AITER backend, MI35x. Run-to-run variance is large here (greedy + continuous-batching nondeterminism), so multiple samples were taken:

Mean difference 0.013 ≪ per-run σ ≈ 0.045 → within noise, no regression. Offline kernel equivalence test: routed weights bit-identical, expert ids exact, shared-expert column differs by ~4e-4 (the fused path computes sigmoid in fp32 vs the old bf16, i.e. strictly more precise).

## Benchmarking and Profiling

torch profiler trace (decode), same config. ATen kernels retain the `_cuda` suffix in their symbol names on ROCm/HIP builds.

| Kernel | Before | After | Notes |
|---|---|---|---|
| `sigmoid_kernel_cuda` (`<8, …sigmoid…>`) | ~5.5 us / layer | **0 occurrences** | eliminated |
| `bfloat16tofloat32_copy_kernel_cuda` (per-layer) | ~4.5 us / layer | **eliminated** | (13 unrelated residual one-offs remain) |
| `_fused_append_shared_experts_with_weights_kernel` | ~4.2 us | 780× @ **3.79 us** | now does sigmoid + cast in-register |

The append kernel fires 780× in the profiling run; with the fusion there are **zero** standalone `sigmoid_kernel_cuda` instances feeding it. Per-invocation saving ≈ **~10 us** (5.5 + 4.5), folded into the existing append kernel. This is decode glue (<0.1% of ITL), so end-to-end throughput impact is within benchmark noise by construction.

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review Process

1. Ping Merge Oncalls to start the PR flow. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - `/tag-run-ci-label`, `/rerun-failed-ci`, `/tag-and-rerun-ci`
4. After green CI and required approvals, ask Merge Oncalls to merge.





































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #27967780275](https://github.com/sgl-project/sglang/actions/runs/27967780275)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27967778273](https://github.com/sgl-project/sglang/actions/runs/27967778273)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
