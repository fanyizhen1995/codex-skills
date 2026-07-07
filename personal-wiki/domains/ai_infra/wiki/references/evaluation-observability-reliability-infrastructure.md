---
type: Reference
title: Evaluation Observability Reliability Infrastructure
description: Source-backed reference for LLM evaluation harnesses, GenAI tracing, observability platforms, and non-NCCL GPU profiling signals.
domain: ai_infra
status: reviewed
aliases:
  - LLM evaluation observability infrastructure
  - GenAI tracing infrastructure
  - evaluation reliability infrastructure
tags:
  - eval-observability-reliability
  - evaluation
  - observability
  - tracing
  - profiling
source_refs:
  - ../../raw/links/opentelemetry-genai-semconv-official-20260707.md
  - ../../raw/links/langsmith-observability-evaluation-official-20260707.md
  - ../../raw/links/phoenix-evaluation-tracing-official-20260707.md
  - ../../raw/links/ragas-evaluation-metrics-official-20260707.md
  - ../../raw/links/lm-evaluation-harness-official-20260707.md
  - ../../raw/links/nvidia-dcgm-gpu-telemetry-official-20260707.md
  - ../../raw/links/nvidia-nsight-systems-profiling-official-20260707.md
updated: 2026-07-07
related:
  - ai-infra-coverage-map.md
  - data-rag-pipeline-infrastructure.md
  - inference-runtime-infrastructure.md
  - nccl-technical-blog-network-observability.md
  - ../references/sglang-github-closed-issues-prs.md
---
# Summary

This reference broadens the `eval-observability-reliability` layer beyond NCCL Inspector, SGLang operational evidence, and RAG-specific Langfuse coverage. It groups seven primary-source notes around four infrastructure surfaces: portable GenAI telemetry schemas, application trace stores, evaluation harnesses, and platform GPU profiling.

The boundary is operational infrastructure. Prompt-writing advice, model architecture details, and benchmark leaderboard claims are outside this page unless the source records run configuration, datasets, metrics, traces, or platform telemetry.

# Telemetry Schema

OpenTelemetry GenAI semantic conventions provide the portable telemetry envelope. They define conventions for GenAI traces, metrics, and events across client calls, server spans, agents, tools, embeddings, and retrieval operations. That makes OpenTelemetry the shared schema layer for recording model-provider metadata and orchestration boundaries across LLM applications. [raw](../../raw/links/opentelemetry-genai-semconv-official-20260707.md)

This is different from NCCL or Spectrum-X observability. NCCL technical-blog evidence records communication-library and fabric-level telemetry such as NCCL Inspector metrics, Prometheus/Grafana dashboards, RAS state, and switch/NIC signals. OpenTelemetry GenAI records application and model-call semantics above that layer. [wiki](nccl-technical-blog-network-observability.md) [raw](../../raw/links/opentelemetry-genai-semconv-official-20260707.md)

# Trace And Experiment Stores

LangSmith and Phoenix provide trace-store and experiment workflows for LLM applications. LangSmith records nested runs for model calls, tools, retrievers, chains, inputs, outputs, latency, errors, metadata, feedback, datasets, evaluators, and experiment results. Phoenix similarly documents LLM traces across model, tool, retriever, and application spans, plus dataset-backed experiments and evaluator scores. [raw](../../raw/links/langsmith-observability-evaluation-official-20260707.md) [raw](../../raw/links/phoenix-evaluation-tracing-official-20260707.md)

These sources support a reusable operator pattern: preserve request traces and offline experiment outputs in one place so an application, retrieval, prompt, model, or serving change can be compared against earlier runs. That sentence is synthesis across LangSmith, Phoenix, Ragas, and lm-evaluation-harness sources; no single source proves every part of the pattern. [raw](../../raw/links/langsmith-observability-evaluation-official-20260707.md) [raw](../../raw/links/phoenix-evaluation-tracing-official-20260707.md) [raw](../../raw/links/ragas-evaluation-metrics-official-20260707.md) [raw](../../raw/links/lm-evaluation-harness-official-20260707.md)

# Evaluation Harnesses

Ragas and lm-evaluation-harness supply the evaluation-harness side of the layer. Ragas documents RAG and LLM evaluation around datasets, metrics, and scored outputs for retrieval and generation quality. lm-evaluation-harness documents benchmark tasks, model backend adapters, CLI run parameters, device placement, output paths, and task metrics. [raw](../../raw/links/ragas-evaluation-metrics-official-20260707.md) [raw](../../raw/links/lm-evaluation-harness-official-20260707.md)

For infrastructure use, the important boundary is run metadata. A benchmark result is not durable evidence unless the harness records the task set, model backend, runtime arguments, device or served-model path, output artifact, and enough environment context to compare later runs. The local source notes support that requirement at the harness-mechanics level; they do not supply a local benchmark corpus or accepted performance baseline. [raw](../../raw/links/lm-evaluation-harness-official-20260707.md) [raw](../../raw/links/nvidia-nsight-systems-profiling-official-20260707.md)

# Platform Profiling And Health

DCGM and Nsight Systems cover the platform side that LLM trace stores cannot see by themselves. DCGM provides GPU health, telemetry, diagnostics, field values, and profiling signals for data-center GPU systems. Nsight Systems provides timeline-oriented CPU/GPU profiling for CUDA workloads, host execution, synchronization, memory operations, kernels, and process/thread behavior. [raw](../../raw/links/nvidia-dcgm-gpu-telemetry-official-20260707.md) [raw](../../raw/links/nvidia-nsight-systems-profiling-official-20260707.md)

Use these sources to connect evaluation or trace anomalies with platform signals, not to assert model quality. For example, a regression triage workflow can pair evaluator scores and request traces with DCGM health fields or an Nsight Systems profile when latency, synchronization, or GPU activity changes. That is a synthesis pattern across the cited observability and profiling sources, not a vendor-specific product claim. [raw](../../raw/links/langsmith-observability-evaluation-official-20260707.md) [raw](../../raw/links/nvidia-dcgm-gpu-telemetry-official-20260707.md) [raw](../../raw/links/nvidia-nsight-systems-profiling-official-20260707.md)

# Adjacent Coverage

[Data RAG Pipeline Infrastructure](data-rag-pipeline-infrastructure.md) already covers Langfuse for RAG-specific traces, retrieval steps, datasets, feedback, and evaluation. This page uses LangSmith, Phoenix, Ragas, and lm-evaluation-harness to broaden beyond RAG-only observability and to make evaluation harness mechanics explicit. [wiki](data-rag-pipeline-infrastructure.md)

[Inference Runtime Infrastructure](inference-runtime-infrastructure.md) records runtime health or metrics surfaces for vLLM, TensorRT-LLM, Triton, llama.cpp, and ONNX Runtime GenAI. This page does not repeat those serving mechanics; it covers the evaluation and trace systems that inspect application behavior around those runtimes. [wiki](inference-runtime-infrastructure.md)

[NCCL Technical Blog Network Observability](nccl-technical-blog-network-observability.md) remains the stronger source for communication and fabric observability. This page adds non-NCCL sources for LLM traces, evaluation datasets, benchmark harnesses, DCGM health telemetry, and Nsight profiling. [wiki](nccl-technical-blog-network-observability.md)

# Coverage Use

Use this page as source-backed coverage for:

- `eval-observability-reliability`: GenAI telemetry schemas, LLM application trace stores, datasets, evaluator outputs, benchmark task/run metadata, GPU health telemetry, and CPU/GPU profiling.
- `data-rag-vector`: only where Ragas, Phoenix, or LangSmith traces explain RAG evaluation and retrieval-quality signals; keep data ingestion and embedding refresh in [Data RAG Pipeline Infrastructure](data-rag-pipeline-infrastructure.md).
- `inference-runtime`: only where evaluation traces or platform profiles inspect runtime behavior; keep runtime scheduler, batching, KV-cache, and model-loading mechanics in [Inference Runtime Infrastructure](inference-runtime-infrastructure.md).
- `hardware-accelerator`: only for DCGM and Nsight platform telemetry/profiling signals; accelerator SKU and parameter evidence stays in the compute accelerator pages.

Remaining gaps include production SLO definitions, alert thresholds, incident/postmortem sources, benchmark environment manifests with captured local results, non-NVIDIA platform observability, and evaluation data governance.

# Citations

- [OpenTelemetry GenAI semantic conventions source note](../../raw/links/opentelemetry-genai-semconv-official-20260707.md)
- [LangSmith observability and evaluation source note](../../raw/links/langsmith-observability-evaluation-official-20260707.md)
- [Phoenix tracing and evaluation source note](../../raw/links/phoenix-evaluation-tracing-official-20260707.md)
- [Ragas evaluation metrics source note](../../raw/links/ragas-evaluation-metrics-official-20260707.md)
- [lm-evaluation-harness source note](../../raw/links/lm-evaluation-harness-official-20260707.md)
- [NVIDIA DCGM source note](../../raw/links/nvidia-dcgm-gpu-telemetry-official-20260707.md)
- [NVIDIA Nsight Systems source note](../../raw/links/nvidia-nsight-systems-profiling-official-20260707.md)
