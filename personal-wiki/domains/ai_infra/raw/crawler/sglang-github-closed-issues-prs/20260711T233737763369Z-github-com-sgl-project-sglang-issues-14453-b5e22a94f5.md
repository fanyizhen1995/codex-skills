---
source_id: sglang-github-closed-issues-prs
title: '[Feature] Integrate new flashinfer optimizations for DeepSeekV3'
canonical_url: https://github.com/sgl-project/sglang/issues/14453
captured_at: '2026-07-11T23:37:37.763369+00:00'
content_hash: b5e22a94f596f8786df366182979b08a919734d6a59002150d483436f8347308
---
# [Feature] Integrate new flashinfer optimizations for DeepSeekV3

URL: https://github.com/sgl-project/sglang/issues/14453
State: closed
Labels: high priority, inactive, deepseek, nvidia
Closed at: 2026-07-11T00:33:08Z
Merged at: 

The following kernels/optimizations have been added recently into flashinfer and should provide speedups for deepseek:

See @leejnau's pinned comment for latest status below:

<!-- 
1. Optimized Router Gemm https://github.com/flashinfer-ai/flashinfer/pull/2019 @harrisonlimh 
2. ~TRTLLM Cutlass moe FC2 + finalizeMoeRouting https://github.com/flashinfer-ai/flashinfer/pull/2020 - Might not require any framework change~ @trevor-m  to look into
3. ~MLA bugfixes https://github.com/flashinfer-ai/flashinfer/pull/2062~ Internal fix, requires no framework change
4. ~Fused topk routing https://github.com/flashinfer-ai/flashinfer/pull/2099~ @leejnau 
5. [feat: Fused RMSNorm + FP4 Quantization Kernels in CuTe-DSL](https://github.com/flashinfer-ai/flashinfer/pull/2233)
6. [feat: Add flashinfer.rope.rope_quantize_fp8_append_paged_kv_cache (fused RoPE + Q + KV cache, supports MLA/GQA/MHA)](https://github.com/flashinfer-ai/flashinfer/pull/2037) @leejnau 
7. cutedsl MoE backend: https://github.com/flashinfer-ai/flashinfer/pull/2398
8. fp8 prefill: https://github.com/flashinfer-ai/flashinfer/pull/2035 and https://github.com/flashinfer-ai/flashinfer/pull/2352. (in light of https://github.com/sgl-project/sglang/pull/7841)
9. Support shared expert fusion for flashinfer trtllm gen MOE
10. Use unified all reduce fusion API https://github.com/flashinfer-ai/flashinfer/pull/2130 @wenscarl 
-->
