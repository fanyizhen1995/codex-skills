---
type: RawSource
title: vLLM README
source_kind: web
url: https://github.com/vllm-project/vllm
captured: 2026-07-07
status: ingested
---
# Source

Official vLLM GitHub repository README: https://github.com/vllm-project/vllm

Captured as a concise source note for `ai_infra` inference-runtime coverage. The full external page was not mirrored; the durable facts below are paraphrased from the official source.

# Captured Facts

- vLLM positions itself as a fast, easy-to-use library for LLM inference and serving.
- The README names PagedAttention as the memory-management mechanism for attention key/value cache.
- The README lists continuous batching of incoming requests as a serving feature.
- The README lists chunked prefill as a serving feature, which makes prefill/decode scheduling part of the runtime surface.
- The README lists prefix caching as a feature, making reusable prompt state a first-class runtime concern.
- vLLM exposes an OpenAI-compatible API server and supports structured outputs, speculative decoding, and streaming outputs.
- Runtime optimization features listed by the README include CUDA/HIP graph use, quantizations, FlashAttention and FlashInfer integration, and optimized CUDA kernels.
- vLLM documents distributed and parallel execution surfaces including tensor parallelism, pipeline parallelism, data parallelism, expert parallelism, and context parallelism.
- The README lists disaggregated prefill, disaggregated encode, and disaggregated prefill/decode systems under advanced serving and scaling features.

# Use In Wiki

Use this source note for vLLM claims about serving APIs, continuous batching, chunked prefill, prefix/KV-cache behavior, PagedAttention, distributed parallel execution modes, and disaggregated serving surfaces.
