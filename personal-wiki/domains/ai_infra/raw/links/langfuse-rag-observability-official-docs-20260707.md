---
type: RawSource
title: Langfuse Tracing And Evaluation Documentation
source_kind: web
url: https://langfuse.com/docs/tracing
captured: 2026-07-07
status: ingested
---
# Source

Official Langfuse tracing documentation: https://langfuse.com/docs/tracing

Captured as a concise source note for `ai_infra` RAG observability coverage. The full external page was not mirrored; the durable facts below are paraphrased from the official source.

# Captured Facts

- Langfuse presents traces as hierarchical records of LLM application execution across steps such as retrieval, tool calls, model calls, and application logic.
- The tracing documentation describes spans and generations, where generations are LLM-related spans that carry model input/output and model metadata.
- Langfuse documents OpenTelemetry-based ingestion and SDK integrations, which makes the trace data portable across application and infrastructure instrumentation.
- The documentation describes scores as evaluation or feedback values attached to traces, observations, sessions, or dataset items.
- Langfuse supports online and offline evaluation workflows, including automated evaluators and human feedback.
- The docs connect traces with datasets, experiments, and prompt/version observability, which is relevant when retrieval behavior or embedding refresh changes need to be compared across runs.
- Langfuse documents tracing of retrieval steps, so production RAG pipelines can inspect retrieved context, generation behavior, user feedback, and evaluation scores together.

# Use In Wiki

Use this source note for production RAG observability claims about traces, retrieval spans, generation records, feedback/evaluation scores, OpenTelemetry ingestion, datasets, experiments, and model/prompt-version observability.
