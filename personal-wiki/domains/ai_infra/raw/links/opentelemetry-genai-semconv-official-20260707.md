---
type: RawSource
title: OpenTelemetry GenAI Semantic Conventions
source_kind: web
url: https://opentelemetry.io/docs/specs/semconv/gen-ai/
captured: 2026-07-07
status: ingested
---
# Source

Official OpenTelemetry GenAI semantic conventions: https://opentelemetry.io/docs/specs/semconv/gen-ai/

Captured as a concise source note for `ai_infra` evaluation, observability, and reliability coverage. The full external page was not mirrored; the durable facts below are paraphrased from the official source.

# Captured Facts

- OpenTelemetry defines semantic conventions for GenAI systems so traces, metrics, and events can use stable attribute names across vendors and applications.
- The GenAI conventions cover client calls, server spans, agents, tools, embeddings, and retrieval-related operations.
- GenAI span attributes include provider, operation, request model, response model, endpoint, system, and usage metadata boundaries.
- The conventions separate model-provider calls from higher-level agent or tool orchestration, which lets infrastructure traces distinguish application orchestration from model-runtime traffic.
- The semantic-convention layer is useful for LLM observability because it standardizes the telemetry envelope rather than prescribing one evaluation product.

# Use In Wiki

Use this source note for claims about OpenTelemetry GenAI trace/span/event/metric boundaries, model-provider metadata, agent/tool/retrieval spans, and portable observability schemas for LLM applications.
