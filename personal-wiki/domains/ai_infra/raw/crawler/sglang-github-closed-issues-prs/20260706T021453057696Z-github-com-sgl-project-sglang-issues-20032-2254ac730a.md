---
source_id: sglang-github-closed-issues-prs
title: '[Feature] Serve LLMs via SGLang runtime as encoders in multimodal generation
  pipelines'
canonical_url: https://github.com/sgl-project/sglang/issues/20032
captured_at: '2026-07-06T02:14:53.057696+00:00'
content_hash: 2254ac730a09a51c6aeb4361732728daad6f2487a3f2d446e6dba8c8c13d3ab7
---
# [Feature] Serve LLMs via SGLang runtime as encoders in multimodal generation pipelines

URL: https://github.com/sgl-project/sglang/issues/20032
State: closed
Labels: inactive
Closed at: 2026-07-06T00:41:18Z
Merged at: 

### Checklist

- [ ] If this is not a feature request but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [ ] Please use English. Otherwise, it will be closed.

### Motivation

## Motivation                                                                                                                                                              
                                                                                                                                                                             
  In the current multimodal generation (diffusion) pipeline, text encoders such as T5, UMT5, and CLIP are loaded as plain PyTorch modules and executed with a straightforward
   forward pass (see `TextEncodingStage` in `runtime/pipelines_core/stages/text_encoding.py`). While functional, this approach does not leverage the highly optimized serving
   capabilities that SGLang's LLM runtime (`srt`) already provides.

  Many of these text encoders are, at their core, large language models. For the text encoding use case, they only require the **prefill** phase (i.e., a single forward pass
   to produce hidden states / embeddings) — effectively acting as **encoders**. In some pipeline configurations, certain LLM components may additionally require
  **autoregressive decoding** (e.g., for captioning or re-captioning stages).

  By routing these LLM workloads through SGLang's `srt` runtime, we can unlock several performance benefits that would directly accelerate end-to-end generation latency and
  throughput.

  ## Proposed Feature

  Allow the multimodal generation pipeline to use SGLang's LLM runtime (`srt`) to serve LLM-based components, where:

  1. **Encoder-only models** (e.g., T5 / UMT5 for text encoding) are served in **prefill-only mode** — no autoregressive decoding is needed; the runtime returns hidden
  states or pooled embeddings after a single forward pass.
  2. **Encoder-decoder or decoder models** that require autoregressive generation are served in the standard decode mode.

  ### Expected Benefits

  - **RadixAttention / Prefix Caching**: Repeated or partially overlapping prompts (common in batch generation or negative prompt reuse) can benefit from prefix cache hits,
  avoiding redundant computation.
  - **Continuous Batching**: Multiple encoding requests can be dynamically batched, improving GPU utilization and throughput under concurrent load.
  - **PagedAttention / Efficient KV Cache Management**: Reduced memory fragmentation for large-batch encoding workloads.
  - **Quantization & Tensor Parallelism**: Leverage `srt`'s existing support for model quantization and multi-GPU tensor parallelism, enabling serving of larger text
  encoders with lower resource overhead.
  - **Unified Serving Infrastructure**: A single SGLang deployment can serve both the LLM encoder components and the diffusion pipeline, simplifying operational complexity.

  ## Current Behavior

  Text encoders are loaded as raw `torch.nn.Module` instances inside `GPUWorker` and invoked directly in `TextEncodingStage.encode_text()`:

  ```python
  # text_encoding.py L264-270
  outputs: BaseEncoderOutput = text_encoder(
      input_ids=input_ids,
      attention_mask=attention_mask,
      output_hidden_states=True,
      use_cache=False,
  )
```

  This bypasses all srt runtime optimizations.

  Possible Approach

  - Introduce an option in PipelineConfig / ServerArgs to specify that certain LLM components should be served via srt (e.g., via a local or remote SGLang endpoint).
  - The TextEncodingStage (and future stages requiring LLM inference) would call the srt runtime instead of directly invoking the Huggingface Transformers module.

  ---

### Related resources

_No response_
