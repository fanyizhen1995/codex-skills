---
type: RawSource
title: EleutherAI lm-evaluation-harness
source_kind: web
url: https://github.com/EleutherAI/lm-evaluation-harness
captured: 2026-07-07
status: ingested
---
# Source

Official EleutherAI lm-evaluation-harness repository: https://github.com/EleutherAI/lm-evaluation-harness

Captured as a concise source note for `ai_infra` evaluation, observability, and reliability coverage. The full external page was not mirrored; the durable facts below are paraphrased from the official source.

# Captured Facts

- lm-evaluation-harness is a framework for evaluating language models across many benchmark tasks.
- The repository documents command-line evaluation runs that specify model backends, model arguments, tasks, device placement, and output paths.
- The harness separates model adapters from task definitions, so the same benchmark task can be run across multiple model-serving or model-loading backends.
- The repository documents support for local and served-model backends, including Hugging Face, vLLM, and API-style providers.
- Evaluation outputs include task metrics and run artifacts that can be stored for later comparison.
- This source supports benchmark-run metadata and harness mechanics, but environment-specific performance claims still need captured hardware, runtime, and configuration context.

# Use In Wiki

Use this source note for lm-evaluation-harness claims about benchmark tasks, model backend adapters, CLI run metadata, metric outputs, and reproducible language-model evaluation runs.
