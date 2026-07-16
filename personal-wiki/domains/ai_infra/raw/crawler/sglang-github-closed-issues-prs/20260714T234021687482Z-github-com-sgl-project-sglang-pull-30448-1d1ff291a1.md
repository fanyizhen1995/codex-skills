---
source_id: sglang-github-closed-issues-prs
title: Refactor FP4 quantization and remove deprecated JIT kernels
canonical_url: https://github.com/sgl-project/sglang/pull/30448
captured_at: '2026-07-14T23:40:21.687482+00:00'
content_hash: 1d1ff291a16b3593232ee1eb8dfe05eb8ffa00c5e50b62de9017375369ef30d3
---
# Refactor FP4 quantization and remove deprecated JIT kernels

URL: https://github.com/sgl-project/sglang/pull/30448
State: closed
Labels: documentation, quant, sgl-kernel, blackwell, run-ci, diffusion, jit-kernel, bypass-fastfail
Closed at: 2026-07-14T01:22:08Z
Merged at: 2026-07-14T01:22:08Z

For MoE, must use Flashinfer CUTLASS on SM120 or trtllm-gen on SM100 (better perf in all cases) (high throughput use Flashinfer Cute-DSL)
For dense GEMM on SM100, use Flashinfer Cute-DSL, on SM120, use Flashinfer CUTLASS
For quantize, use backend = cute-dsl of fp4_quantize in Flashinfer

Fix https://github.com/sgl-project/sglang/issues/28663





































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29263311113](https://github.com/sgl-project/sglang/actions/runs/29263311113)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29263310306](https://github.com/sgl-project/sglang/actions/runs/29263310306)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
