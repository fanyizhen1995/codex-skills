---
type: RawSource
title: ONNX Runtime GenAI Configuration And API Documentation
source_kind: web
url: https://onnxruntime.ai/docs/genai/reference/config.html
secondary_urls:
  - https://onnxruntime.ai/docs/genai/api/python.html
captured: 2026-07-07
status: ingested
---
# Source

Official ONNX Runtime GenAI documentation:

- https://onnxruntime.ai/docs/genai/reference/config.html
- https://onnxruntime.ai/docs/genai/api/python.html

Captured as a concise source note for `ai_infra` inference-runtime coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- ONNX Runtime GenAI uses a `genai_config.json` file to describe model, tokenizer, provider, search, and generation settings for model execution.
- The config reference includes model-level settings such as model type, context length, vocabulary size, end-of-sequence token IDs, padding token IDs, decoder head counts, hidden size, and memory-related dimensions.
- The model section describes decoder inputs and outputs, including `past_key_names` and `present_key_names`, which tie the runtime to KV-cache style generation state.
- The config reference documents provider settings and lists execution providers such as CPU, CUDA, DirectML, OpenVINO, QNN, and WebGPU.
- The search section carries generation controls such as maximum length, minimum length, beam count, sampling options, repetition penalty, top-k, top-p, temperature, and early stopping.
- The Python API exposes `Config`, `Model`, `GeneratorParams`, `Generator`, and `Tokenizer` classes.
- `GeneratorParams` can set model inputs, search options, and graph-capture settings.
- `Generator` exposes token generation lifecycle methods, including generating the next token, retrieving logits, retrieving generated tokens, rewinding the generator, checking completion, and setting active adapters.

# Use In Wiki

Use this source note for ONNX Runtime GenAI claims about runtime configuration, provider selection, KV-cache input/output naming, search/generation controls, graph capture, and token-generation APIs.
