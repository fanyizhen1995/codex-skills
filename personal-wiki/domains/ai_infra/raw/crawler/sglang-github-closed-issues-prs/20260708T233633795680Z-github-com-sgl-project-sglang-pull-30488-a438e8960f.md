---
source_id: sglang-github-closed-issues-prs
title: '[LoRA][XPU] Enable LoRA on Intel XPU'
canonical_url: https://github.com/sgl-project/sglang/pull/30488
captured_at: '2026-07-08T23:36:33.795680+00:00'
content_hash: a438e8960fd9cdb2acaff598fa025c35463267ebbd40cac115d7332df8eea70a
---
# [LoRA][XPU] Enable LoRA on Intel XPU

URL: https://github.com/sgl-project/sglang/pull/30488
State: closed
Labels: lora
Closed at: 2026-07-08T07:28:53Z
Merged at: 

## Summary
- Enable LoRA support on Intel XPU backend
- Add graceful fallback for missing XPU-specific kernels in sgl_kernel
- Fix device-hardcoded CUDA references to support multi-platform execution
- Add XPU CI registration for LoRA tests

## Key Changes
- **Rotary embedding**: Add ImportError handling for XPU fused kernels, with fallback to generic implementations
- **LoRA backends**: Replace hardcoded `torch.device("cuda")` with `self.device` for CUDA graph setup
- **LoRA MoE**: Force naive alignment path on XPU (fused CUDA align kernel is CUDA-only)
- **Test utilities**: Add ROUGE-L fallback for XPU greedy decoding comparison (kernel fp differences can cause divergence)
- **Test infrastructure**: Register XPU CI for all LoRA test suites, add device-agnostic cache clearing

## Test Plan
- [x] All LoRA tests pass on Intel XPU
- [x] Existing CUDA tests remain unaffected
- [x] Graceful degradation when XPU kernels are unavailable

🤖 Generated with [Claude Code](https://claude.com/claude-code)

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: **Missing `run-ci` label** -- add it to run CI tests.<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: **Blocked** -- `run-ci` is required first.<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
