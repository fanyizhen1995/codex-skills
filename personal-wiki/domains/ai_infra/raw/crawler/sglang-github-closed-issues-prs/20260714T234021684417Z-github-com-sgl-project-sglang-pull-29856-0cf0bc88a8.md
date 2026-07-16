---
source_id: sglang-github-closed-issues-prs
title: Fix BF16 routing bias dtype for TRT-LLM MoE
canonical_url: https://github.com/sgl-project/sglang/pull/29856
captured_at: '2026-07-14T23:40:21.684417+00:00'
content_hash: 0cf0bc88a803317c7fa1e39926473ce373bb721f3b82a38d584fb03b7473eaff
---
# Fix BF16 routing bias dtype for TRT-LLM MoE

URL: https://github.com/sgl-project/sglang/pull/29856
State: closed
Labels: deepseek
Closed at: 2026-07-14T03:42:08Z
Merged at: 

## Summary
- initialize MoE correction bias as BF16 for FlashInfer TRT-LLM gate paths
- add unit coverage for DeepSeek and GLM gate dtype selection

## Root Cause
For [nvidia/GLM-5.2-NVFP4](https://huggingface.co/nvidia/GLM-5.2-NVFP4), speculative draft construction can instantiate an unquantized BF16 MoE gate while `--speculative-moe-runner-backend flashinfer_trtllm` selects the FlashInfer TRT-LLM MoE runner. The gate routing bias kept the default FP32 dtype unless the main `modelopt_fp4` quantization branch was active. The TRT-LLM runner expects that routing-bias tensor to match the BF16 hidden states, so draft execution can hit a dtype mismatch.

This patch selects the BF16 bias dtype at layer initialization whenever the FlashInfer TRT-LLM MoE backend is active, avoiding runtime casts.































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28543287170](https://github.com/sgl-project/sglang/actions/runs/28543287170)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28543286942](https://github.com/sgl-project/sglang/actions/runs/28543286942)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
