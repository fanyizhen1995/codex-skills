---
type: RawSource
title: LangSmith Observability And Evaluation Documentation
source_kind: web
url: https://docs.smith.langchain.com/observability
secondary_urls:
  - https://docs.smith.langchain.com/evaluation
captured: 2026-07-07
status: ingested
---
# Source

Official LangSmith observability documentation: https://docs.smith.langchain.com/observability

Official LangSmith evaluation documentation: https://docs.smith.langchain.com/evaluation

Captured as a concise source note for `ai_infra` evaluation, observability, and reliability coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- LangSmith observability centers on traces for LLM application execution, with nested runs that show model calls, tool calls, retrievers, chains, and application logic.
- The observability documentation connects traces with metadata, tags, inputs, outputs, latency, errors, and feedback, making traces usable for production debugging and review.
- LangSmith evaluation uses datasets and examples as reusable evaluation inputs.
- Evaluation runs compare a target system or function against evaluators and store experiment results.
- The evaluation workflow supports regression-style comparison because experiments preserve outputs, evaluator results, and dataset context across runs.
- LangSmith belongs in infrastructure coverage when it is used to store traces, datasets, evaluator outputs, feedback, and experiment history, not when the topic is prompt wording itself.

# Use In Wiki

Use this source note for LangSmith claims about trace trees, run metadata, feedback, datasets, evaluators, experiments, and regression-style LLM application evaluation workflows.
