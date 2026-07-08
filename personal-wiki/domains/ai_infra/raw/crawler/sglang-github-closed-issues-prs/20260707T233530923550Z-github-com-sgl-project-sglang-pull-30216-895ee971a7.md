---
source_id: sglang-github-closed-issues-prs
title: '[CPU] add fused_qk_gemma_norm and refactor norm kernel implementation'
canonical_url: https://github.com/sgl-project/sglang/pull/30216
captured_at: '2026-07-07T23:35:30.923550+00:00'
content_hash: 895ee971a768373be7e5b76dc8b54b3847e8bf35fa66631d1e1f79d0ed977221
---
# [CPU] add fused_qk_gemma_norm and refactor norm kernel implementation

URL: https://github.com/sgl-project/sglang/pull/30216
State: closed
Labels: sgl-kernel, intel, cpu, run-ci
Closed at: 2026-07-07T00:52:59Z
Merged at: 2026-07-07T00:52:59Z


<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

CPU norm kernels in sgl-kernel (L2Norm, RMSNorm, Gemma variants, LayerNorm, gated RMSNorm, and fused add paths) were implemented as separate, largely duplicated loops. Each kernel reimplemented the same reduce → scale → (weight / bias / gate) logic with slightly different tensor layouts and stride handling.

This PR refactors those kernels into a single trait-based framework. The goal is to:

- Reduce maintenance cost when adding or changing norm variants (notably Gemma / QK-style RMSNorm)
- Unify 2D / 3D / 4D input handling in one code path
- Keep the existing public `torch.ops.sgl_kernel.*_cpu` APIs unchanged
- Improve performance on AVX512 via a BF16 fast path and faster approximate exp for `SiLU`
- Add `fused_qk_gemma_norm` for Qwen3.5

## Modifications

Core refactor (sgl-kernel/csrc/cpu/norm.cpp)
Introduce shared infrastructure:

- NormParams: normalizes 2D / 3D / 4D inputs into a logical [B, H, T, D] layout with stride-aware input indexing and contiguous output
- NormMode + NormTraits: compile-time flags for weight, bias, shift, mean, and gate; shared apply_* helpers
- NormReduceGeneric: generic vectorized reduce + apply path for all modes
- NormReduce<M, BFloat16, D> (AVX512): specialized fast path for BF16 when D ∈ {32, 64, 128, 256, 512}

Migrate all existing CPU norm ops onto the unified framework:

- l2norm_cpu
- rmsnorm_cpu, fused_add_rmsnorm_cpu
- gemma_rmsnorm_cpu, gemma3_rmsnorm_cpu, gemma4_rmsnorm_cpu, gemma_fused_add_rmsnorm_cpu
- layernorm_cpu, fused_add_layernorm_cpu
- fused_rmsnorm_gated_cpu


## Accuracy Tests

`test/registered/cpu/test_norm.py`: reorganize and extend coverage

- Gemma / Gemma3 (including 4D QK-style layout), Gemma4 (with_scale / scale_shift), gated RMSNorm, LayerNorm
- Non-standard hidden sizes (e.g. hidden_size=33) to exercise tail handling

## Speed Tests and Profiling

Benchmark (bf16, q_heads=16, kv_heads=4, head_dim=256):

- batch=1: 6.280 us (fused) vs 71.551 us (native), 11.39x speedup
- batch=4000: 294.770 us (fused) vs 2387.317 us (native), 8.10x speedup

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28774990322](https://github.com/sgl-project/sglang/actions/runs/28774990322)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28774990156](https://github.com/sgl-project/sglang/actions/runs/28774990156)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
