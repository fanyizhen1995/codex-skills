---
type: RawSource
title: TensorRT-LLM KV Cache And Serve Documentation
source_kind: web
url: https://nvidia.github.io/TensorRT-LLM/features/kvcache.html
secondary_urls:
  - https://nvidia.github.io/TensorRT-LLM/commands/trtllm-serve.html
captured: 2026-07-07
status: ingested
---
# Source

Official NVIDIA TensorRT-LLM documentation:

- https://nvidia.github.io/TensorRT-LLM/features/kvcache.html
- https://nvidia.github.io/TensorRT-LLM/commands/trtllm-serve.html

Captured as a concise source note for `ai_infra` inference-runtime coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- TensorRT-LLM documents KV cache as a generation-time optimization that stores key/value pairs from prior tokens so future tokens can reuse them instead of recomputing them.
- Its KV cache model uses blocks as the storage unit. A block represents a fixed number of tokens and contains data from multiple layers.
- TensorRT-LLM exposes KV cache controls through `KvCacheConfig`, including memory fraction, free memory fraction, maximum token counts, host cache size, attention-window settings, and reuse controls.
- TensorRT-LLM documents block reuse across requests. It identifies matching blocks with a radix search tree and says the feature is enabled by default.
- The documentation describes priority-based eviction and host offloading as runtime choices for KV cache lifecycle and memory pressure.
- The `trtllm-serve` command starts an OpenAI-compatible server for TensorRT-LLM models.
- `trtllm-serve` exposes endpoints for model listing, completions, chat completions, health, metrics, and version reporting.
- `trtllm-serve` supports server options for model path, host, port, tensor parallelism, pipeline parallelism, expert parallelism, backend selection, served model name, log level, and dynamic module loading.
- The serving documentation includes metrics for request activity, GPU memory, token counts, cache behavior, and in-flight batching.

# Use In Wiki

Use this source note for TensorRT-LLM claims about KV-cache block lifecycle, reuse, offload, OpenAI-compatible serving, runtime parallelism knobs, and serving metrics.
