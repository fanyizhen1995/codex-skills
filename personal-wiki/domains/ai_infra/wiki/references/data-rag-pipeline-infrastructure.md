---
type: Reference
title: Data RAG Pipeline Infrastructure
description: Source-backed reference for data/RAG ingestion, embedding workers, refresh workflows, metadata lineage, and RAG observability beyond vector index mechanics.
domain: ai_infra
status: reviewed
aliases:
  - RAG data pipeline infrastructure
  - embedding pipeline infrastructure
  - RAG observability pipeline
tags:
  - data-rag-vector
  - rag
  - embedding
  - data-pipeline
  - observability
source_refs:
  - ../../raw/links/ray-data-pipeline-official-docs-20260707.md
  - ../../raw/links/apache-flink-stateful-stream-processing-official-docs-20260707.md
  - ../../raw/links/huggingface-text-embeddings-inference-official-docs-20260707.md
  - ../../raw/links/datahub-openlineage-metadata-lineage-official-docs-20260707.md
  - ../../raw/links/langfuse-rag-observability-official-docs-20260707.md
  - data-rag-vector-infrastructure.md
updated: 2026-07-07
related:
  - ai-infra-coverage-map.md
  - data-rag-vector-infrastructure.md
  - inference-runtime-infrastructure.md
---
# Summary

This page extends the `data-rag-vector` layer beyond vector database and index mechanics. It covers the pipeline surfaces around retrieval systems: data ingestion and transforms, streaming refresh, embedding workers, metadata lineage, and RAG observability.

The selected sources are deliberately bounded. Ray Data supplies batch and object-store-oriented data processing evidence; Flink supplies checkpointed streaming refresh evidence; Hugging Face Text Embeddings Inference supplies an embedding-serving boundary; DataHub and OpenLineage supply metadata and lineage boundaries; Langfuse supplies RAG trace and evaluation evidence. Vector store internals remain in [Data RAG Vector Infrastructure](data-rag-vector-infrastructure.md).

# Pipeline Boundaries

RAG data infrastructure should be treated as a pipeline, not only as a vector index. A durable system needs at least five source-backed control points:

- `source ingestion and transforms`: Ray Data documents distributed reads, dataset transforms, batch inference, object-store examples, and worker resource controls for ML data pipelines. [raw](../../raw/links/ray-data-pipeline-official-docs-20260707.md)
- `streaming or incremental refresh`: Flink documents stateful stream processing, event-time processing, durable checkpoints, source-position recovery, and replayable sources such as Kafka brokers. [raw](../../raw/links/apache-flink-stateful-stream-processing-official-docs-20260707.md)
- `embedding generation`: Hugging Face Text Embeddings Inference documents an embedding-serving process with HTTP APIs, CPU/GPU images, model/revision choices, request queuing, token and batch limits, health, and Prometheus metrics. [raw](../../raw/links/huggingface-text-embeddings-inference-official-docs-20260707.md)
- `metadata and lineage`: DataHub ingestion recipes and OpenLineage run/job/dataset events provide a catalog and event envelope for recording which sources, jobs, and datasets produced embedding or retrieval artifacts. [raw](../../raw/links/datahub-openlineage-metadata-lineage-official-docs-20260707.md)
- `RAG observability`: Langfuse tracing records retrieval, generation, scores, datasets, experiments, and feedback, so a RAG pipeline can connect retrieved context with model output and evaluation signals. [raw](../../raw/links/langfuse-rag-observability-official-docs-20260707.md)

# Ingestion And Refresh

Batch ingestion and refresh jobs need dataset-level infrastructure before data reaches a vector store. Ray Data provides the source-backed batch side: it can read from file and table sources, apply dataset transformations, repartition, write outputs, and run batch inference over records. In a RAG pipeline, that maps naturally to document loading, parsing/enrichment, embedding generation, and output writes, but this page treats that as synthesis across Ray Data plus embedding-worker evidence rather than a Ray-only product claim. [raw](../../raw/links/ray-data-pipeline-official-docs-20260707.md) [raw](../../raw/links/huggingface-text-embeddings-inference-official-docs-20260707.md)

Streaming refresh has different failure boundaries. Flink's checkpoint model snapshots operator state and source positions to durable storage; recovery restores both and replays input from a rewindable source position. For RAG infrastructure, the important claim is not that every embedding refresh is exactly-once by default. The source-backed claim is narrower: a refresh pipeline can be designed around checkpointed state and replayable source positions so document-change processing can recover after failure without guessing where the stream stopped. [raw](../../raw/links/apache-flink-stateful-stream-processing-official-docs-20260707.md)

The vector store lifecycle from the prior page remains the downstream index side. Milvus evidence already covers growing data, sealed segments, compaction, index building, and query loading; this page adds the upstream data and embedding pipeline that produces or refreshes those vectors. [wiki](data-rag-vector-infrastructure.md)

# Embedding Worker Surface

Embedding generation deserves its own serving boundary. TEI supports model id and revision selection, batch/token controls, CPU/GPU deployment variants, request queueing, health endpoints, and metrics. Those are operational controls for an embedding worker pool; they are different from vector database index parameters, even though both affect retrieval quality and latency. [raw](../../raw/links/huggingface-text-embeddings-inference-official-docs-20260707.md)

For refresh workflows, the embedding worker should be considered a versioned dependency of the data pipeline. DataHub/OpenLineage can record job, dataset, run, schema, ownership, and lineage metadata; Langfuse can record retrieval and generation traces plus evaluation scores. Together these sources support an infrastructure pattern where an embedding refresh is tied to source dataset identity, pipeline run identity, embedding model or serving revision, downstream vector index state, and observed retrieval behavior. This sentence is synthesis across the cited sources, not a claim that any single source implements the entire workflow. [raw](../../raw/links/datahub-openlineage-metadata-lineage-official-docs-20260707.md) [raw](../../raw/links/langfuse-rag-observability-official-docs-20260707.md) [raw](../../raw/links/huggingface-text-embeddings-inference-official-docs-20260707.md)

# Metadata Governance

Metadata governance is the piece that keeps RAG data pipelines auditable. DataHub ingestion recipes define sources, transformers, and sinks, while OpenLineage standardizes events around jobs, runs, datasets, and facets. Those boundaries can identify which source collection, pipeline job, and produced dataset fed a vector index or evaluation dataset. [raw](../../raw/links/datahub-openlineage-metadata-lineage-official-docs-20260707.md)

This page should not overstate governance coverage. The local source set supports ingestion, lineage, catalog, schema/ownership, and run/dataset metadata. It does not yet cover access policy, tenant isolation, PII controls, deletion propagation, retention, cost attribution, or legal governance for RAG corpora.

# RAG Observability

RAG observability needs retrieval-level traces, not only model-server health. Langfuse documents hierarchical traces with retrieval steps, model generations, scores, datasets, experiments, user feedback, and OpenTelemetry ingestion. That supports an operator view where retrieval context, generated answers, feedback, and evaluation scores can be inspected together after an ingestion or embedding refresh. [raw](../../raw/links/langfuse-rag-observability-official-docs-20260707.md)

This page should also keep RAG observability separate from the existing NCCL and inference-runtime observability pages. NCCL technical-blog evidence covers GPU communication, fabric telemetry, Prometheus/Grafana, and RAS; inference-runtime evidence covers health or metrics surfaces for serving systems. Langfuse covers application/RAG traces and evaluation signals. These are adjacent layers, not duplicates. [wiki](nccl-technical-blog-network-observability.md) [wiki](inference-runtime-infrastructure.md) [raw](../../raw/links/langfuse-rag-observability-official-docs-20260707.md)

# Coverage Use

Use this page as source-backed coverage for:

- `data-rag-vector`: ingestion and transform jobs, checkpointed refresh workflows, embedding workers, metadata lineage, and production RAG tracing/evaluation.
- `eval-observability-reliability`: only where Langfuse trace/evaluation evidence explains retrieval quality or RAG feedback loops; this page does not replace broader observability, SLO, incident, or benchmark infrastructure coverage.
- `orchestration-scheduling`: only where Ray Data or Flink jobs explain data-pipeline execution boundaries; this page does not replace Ray cluster, workflow scheduler, Kubernetes, or batch-queue coverage.

Remaining gaps include direct Kafka Connect or Kafka Streams primary-source coverage, Airflow/Dagster/Prefect orchestration evidence, object-store table-format governance, deletion and retention propagation, embedding model/version drift policies, retrieval-quality alerting, and production incident evidence for RAG pipelines.

# Citations

- [Ray Data pipeline source note](../../raw/links/ray-data-pipeline-official-docs-20260707.md)
- [Apache Flink stateful stream-processing source note](../../raw/links/apache-flink-stateful-stream-processing-official-docs-20260707.md)
- [Hugging Face TEI source note](../../raw/links/huggingface-text-embeddings-inference-official-docs-20260707.md)
- [DataHub and OpenLineage metadata-lineage source note](../../raw/links/datahub-openlineage-metadata-lineage-official-docs-20260707.md)
- [Langfuse RAG observability source note](../../raw/links/langfuse-rag-observability-official-docs-20260707.md)
- [Data RAG Vector Infrastructure](data-rag-vector-infrastructure.md)
