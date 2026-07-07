---
type: RawSource
title: Arize Phoenix Tracing And Evaluation Documentation
source_kind: web
url: https://arize.com/docs/phoenix/tracing
secondary_urls:
  - https://arize.com/docs/phoenix/evaluation
captured: 2026-07-07
status: ingested
---
# Source

Official Arize Phoenix tracing documentation: https://arize.com/docs/phoenix/tracing

Official Arize Phoenix evaluation documentation: https://arize.com/docs/phoenix/evaluation

Captured as a concise source note for `ai_infra` evaluation, observability, and reliability coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- Phoenix documents tracing for LLM applications, including spans that capture calls across models, tools, retrievers, and application steps.
- Phoenix traces are organized so an operator can inspect request execution, latency, errors, inputs, outputs, and nested component behavior.
- Phoenix evaluation documentation covers evaluator workflows for LLM applications, including dataset-backed experiments and scored outputs.
- Phoenix connects observability and evaluation by letting traces and experiments carry annotations or scores that can be inspected after an application change.
- Phoenix supports OpenTelemetry-style instrumentation paths, which makes it adjacent to the OpenTelemetry GenAI semantic-convention layer rather than a replacement for it.

# Use In Wiki

Use this source note for Phoenix claims about LLM tracing, span inspection, dataset-backed experiments, evaluator scores, and the connection between production traces and offline evaluation.
