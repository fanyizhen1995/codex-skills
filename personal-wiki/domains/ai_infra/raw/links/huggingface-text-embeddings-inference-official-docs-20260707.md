---
type: RawSource
title: Hugging Face Text Embeddings Inference
source_kind: web
url: https://huggingface.co/docs/text-embeddings-inference/index
captured: 2026-07-07
status: ingested
---
# Source

Official Hugging Face Text Embeddings Inference documentation: https://huggingface.co/docs/text-embeddings-inference/index

Captured as a concise source note for `ai_infra` embedding worker coverage. The full external page was not mirrored; the durable facts below are paraphrased from the official source.

# Captured Facts

- Text Embeddings Inference is a toolkit for deploying and serving open-source text embedding and sequence-classification models.
- The documentation describes a Docker image and a serving command that exposes an HTTP API for embedding requests.
- TEI supports CPU and GPU deployments, with separate image variants for CUDA, ROCm, CPU, and other environments.
- The project documents production-serving features such as token-based batching, request queuing, Prometheus metrics, health endpoints, and model download/caching behavior.
- TEI supports text embedding models from the Hugging Face Hub and includes options for model id, revision, pooling, dtype, max client batch size, max batch tokens, and other serving constraints.
- The API examples include an embeddings endpoint that accepts input text and returns embedding vectors.
- TEI documents OpenAI-compatible embedding API support, which makes it relevant to RAG systems that already use OpenAI-style embedding clients.

# Use In Wiki

Use this source note for embedding-generation worker claims about embedding-serving boundaries, model selection, batch/token controls, request queueing, health and metrics surfaces, CPU/GPU deployment choices, and OpenAI-compatible embedding APIs.
