---
type: Reference
title: Data RAG Pipeline Infrastructure
description: Source-backed reference for data/RAG ingestion, workflow orchestration, embedding workers, table lifecycle, metadata lineage, and RAG observability beyond vector index mechanics.
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
  - ../../raw/links/kafka-connect-streams-official-docs-20260707.md
  - ../../raw/links/apache-airflow-workflow-scheduling-official-docs-20260707.md
  - ../../raw/links/dagster-assets-runs-official-docs-20260707.md
  - ../../raw/links/prefect-flow-task-scheduling-official-docs-20260707.md
  - ../../raw/links/apache-iceberg-table-governance-official-docs-20260707.md
  - ../../raw/links/delta-lake-table-lifecycle-official-docs-20260707.md
  - ../../raw/links/apache-hudi-table-lifecycle-official-docs-20260707.md
  - data-rag-vector-infrastructure.md
updated: 2026-07-07
related:
  - ai-infra-coverage-map.md
  - data-rag-vector-infrastructure.md
  - inference-runtime-infrastructure.md
---
# Summary

This page extends the `data-rag-vector` layer beyond vector database and index mechanics. It covers the pipeline surfaces around retrieval systems: data ingestion and transforms, streaming refresh, workflow orchestration, embedding workers, metadata lineage, table-format lifecycle governance, and RAG observability.

The selected sources are deliberately bounded. Ray Data supplies batch and object-store-oriented data processing evidence; Flink supplies checkpointed streaming refresh evidence; Kafka Connect and Kafka Streams supply connector and stream-processor boundaries; Airflow, Dagster, and Prefect supply workflow scheduler evidence; Hugging Face Text Embeddings Inference supplies an embedding-serving boundary; DataHub and OpenLineage supply metadata and lineage boundaries; Iceberg, Delta Lake, and Hudi supply object-store table lifecycle evidence; Langfuse supplies RAG trace and evaluation evidence. Vector store internals remain in [Data RAG Vector Infrastructure](data-rag-vector-infrastructure.md).

# Pipeline Boundaries

RAG data infrastructure should be treated as a pipeline, not only as a vector index. A durable system needs source-backed control points across ingestion, refresh, orchestration, embedding, metadata, table lifecycle, and observability:

- `source ingestion and transforms`: Ray Data documents distributed reads, dataset transforms, batch inference, object-store examples, and worker resource controls for ML data pipelines. [raw](../../raw/links/ray-data-pipeline-official-docs-20260707.md)
- `streaming or incremental refresh`: Flink documents stateful stream processing, event-time processing, durable checkpoints, source-position recovery, and replayable sources such as Kafka brokers. Kafka Connect adds source/sink connector, task, worker, and Kafka-backed offset/status/config boundaries, while Kafka Streams adds processor topologies, local state stores, and changelog-backed recovery. [raw](../../raw/links/apache-flink-stateful-stream-processing-official-docs-20260707.md) [raw](../../raw/links/kafka-connect-streams-official-docs-20260707.md)
- `workflow orchestration`: Airflow DAGs and tasks, Dagster assets/jobs/runs, and Prefect flows/tasks/deployments give source-backed execution boundaries for scheduled or event-driven refresh workflows. [raw](../../raw/links/apache-airflow-workflow-scheduling-official-docs-20260707.md) [raw](../../raw/links/dagster-assets-runs-official-docs-20260707.md) [raw](../../raw/links/prefect-flow-task-scheduling-official-docs-20260707.md)
- `embedding generation`: Hugging Face Text Embeddings Inference documents an embedding-serving process with HTTP APIs, CPU/GPU images, model/revision choices, request queuing, token and batch limits, health, and Prometheus metrics. [raw](../../raw/links/huggingface-text-embeddings-inference-official-docs-20260707.md)
- `metadata and lineage`: DataHub ingestion recipes and OpenLineage run/job/dataset events provide a catalog and event envelope for recording which sources, jobs, and datasets produced embedding or retrieval artifacts. [raw](../../raw/links/datahub-openlineage-metadata-lineage-official-docs-20260707.md)
- `table lifecycle governance`: Iceberg, Delta Lake, and Hudi add snapshot or transaction-log style table states, schema evolution, row-level delete/update/upsert surfaces, and cleanup or retention operations for object-store tables. [raw](../../raw/links/apache-iceberg-table-governance-official-docs-20260707.md) [raw](../../raw/links/delta-lake-table-lifecycle-official-docs-20260707.md) [raw](../../raw/links/apache-hudi-table-lifecycle-official-docs-20260707.md)
- `RAG observability`: Langfuse tracing records retrieval, generation, scores, datasets, experiments, and feedback, so a RAG pipeline can connect retrieved context with model output and evaluation signals. [raw](../../raw/links/langfuse-rag-observability-official-docs-20260707.md)

# Ingestion And Refresh

Batch ingestion and refresh jobs need dataset-level infrastructure before data reaches a vector store. Ray Data provides the source-backed batch side: it can read from file and table sources, apply dataset transformations, repartition, write outputs, and run batch inference over records. In a RAG pipeline, that maps naturally to document loading, parsing/enrichment, embedding generation, and output writes, but this page treats that as synthesis across Ray Data plus embedding-worker evidence rather than a Ray-only product claim. [raw](../../raw/links/ray-data-pipeline-official-docs-20260707.md) [raw](../../raw/links/huggingface-text-embeddings-inference-official-docs-20260707.md)

Streaming refresh has different failure boundaries. Flink's checkpoint model snapshots operator state and source positions to durable storage; recovery restores both and replays input from a rewindable source position. Kafka Connect adds a connector layer for moving external-system changes into or out of Kafka topics, with source/sink connectors split into tasks and coordinated by workers. Kafka Streams adds the application layer for processing Kafka topics through processor topologies, state stores, and changelog-backed state recovery. For RAG infrastructure, the important claim is not that every embedding refresh is exactly-once by default. The source-backed claim is narrower: a refresh pipeline can be designed around connector offsets, checkpointed state, replayable source positions, and state-store recovery so document-change processing can recover after failure without guessing where the stream stopped. This is synthesis across the Kafka and Flink sources. [raw](../../raw/links/apache-flink-stateful-stream-processing-official-docs-20260707.md) [raw](../../raw/links/kafka-connect-streams-official-docs-20260707.md)

The vector store lifecycle from the prior page remains the downstream index side. Milvus evidence already covers growing data, sealed segments, compaction, index building, and query loading; this page adds the upstream data and embedding pipeline that produces or refreshes those vectors. [wiki](data-rag-vector-infrastructure.md)

# Workflow Orchestration

Workflow schedulers are a separate control plane from stream processors and vector databases. Airflow models workflows as DAGs with tasks, dependencies, DAG runs, scheduler-created runs, task states, and retry behavior. That is useful when document parsing, embedding, index rebuild, evaluation, or cleanup happens in scheduled jobs rather than a continuously running stream. [raw](../../raw/links/apache-airflow-workflow-scheduling-official-docs-20260707.md)

Dagster and Prefect expose adjacent orchestration boundaries. Dagster's asset model makes produced datasets or artifacts first-class, with asset dependencies, jobs, runs, schedules, sensors, and materialization metadata. Prefect organizes workflows as flows with tasks, deployments, schedules, workers, and work pools. In a RAG data platform, these sources support a durable distinction: the scheduler controls when work runs and what dependencies are satisfied; it does not by itself prove that downstream vector indexes or RAG caches observed every source-table lifecycle event. [raw](../../raw/links/dagster-assets-runs-official-docs-20260707.md) [raw](../../raw/links/prefect-flow-task-scheduling-official-docs-20260707.md)

# Embedding Worker Surface

Embedding generation deserves its own serving boundary. TEI supports model id and revision selection, batch/token controls, CPU/GPU deployment variants, request queueing, health endpoints, and metrics. Those are operational controls for an embedding worker pool; they are different from vector database index parameters, even though both affect retrieval quality and latency. [raw](../../raw/links/huggingface-text-embeddings-inference-official-docs-20260707.md)

For refresh workflows, the embedding worker should be considered a versioned dependency of the data pipeline. DataHub/OpenLineage can record job, dataset, run, schema, ownership, and lineage metadata; Langfuse can record retrieval and generation traces plus evaluation scores. Together these sources support an infrastructure pattern where an embedding refresh is tied to source dataset identity, pipeline run identity, embedding model or serving revision, downstream vector index state, and observed retrieval behavior. This sentence is synthesis across the cited sources, not a claim that any single source implements the entire workflow. [raw](../../raw/links/datahub-openlineage-metadata-lineage-official-docs-20260707.md) [raw](../../raw/links/langfuse-rag-observability-official-docs-20260707.md) [raw](../../raw/links/huggingface-text-embeddings-inference-official-docs-20260707.md)

# Metadata Governance

Metadata governance is the piece that keeps RAG data pipelines auditable. DataHub ingestion recipes define sources, transformers, and sinks, while OpenLineage standardizes events around jobs, runs, datasets, and facets. Those boundaries can identify which source collection, pipeline job, and produced dataset fed a vector index or evaluation dataset. [raw](../../raw/links/datahub-openlineage-metadata-lineage-official-docs-20260707.md)

Table formats add lifecycle semantics below the scheduler and above raw object-store files. Iceberg uses metadata and snapshots for consistent table states, schema and partition evolution, row-level update/delete support through engines, snapshot expiration, and orphan-file cleanup. Delta Lake uses a transaction log for table versions and metadata, DML operations such as delete/update/merge, schema enforcement/evolution, time travel, and VACUUM retention. Hudi uses table types, a timeline of actions, upsert/delete semantics, schema evolution, compaction, cleaning, and retention policies. These are source-backed table lifecycle controls, not a guarantee that embeddings or vector indexes are automatically deleted. [raw](../../raw/links/apache-iceberg-table-governance-official-docs-20260707.md) [raw](../../raw/links/delta-lake-table-lifecycle-official-docs-20260707.md) [raw](../../raw/links/apache-hudi-table-lifecycle-official-docs-20260707.md)

This page should not overstate governance coverage. The local source set now supports ingestion, workflow orchestration, lineage, catalog, schema/ownership, run/dataset metadata, table snapshots or transaction logs, table delete/update/upsert surfaces, and table cleanup/retention mechanics. It does not yet cover complete RAG access policy, tenant isolation, PII controls, legal governance, or proof that source-table deletes and retention events propagate into every embedding store, vector index, cache, and evaluation dataset.

# RAG Observability

RAG observability needs retrieval-level traces, not only model-server health. Langfuse documents hierarchical traces with retrieval steps, model generations, scores, datasets, experiments, user feedback, and OpenTelemetry ingestion. That supports an operator view where retrieval context, generated answers, feedback, and evaluation scores can be inspected together after an ingestion or embedding refresh. [raw](../../raw/links/langfuse-rag-observability-official-docs-20260707.md)

This page should also keep RAG observability separate from the existing NCCL and inference-runtime observability pages. NCCL technical-blog evidence covers GPU communication, fabric telemetry, Prometheus/Grafana, and RAS; inference-runtime evidence covers health or metrics surfaces for serving systems. Langfuse covers application/RAG traces and evaluation signals. These are adjacent layers, not duplicates. [wiki](nccl-technical-blog-network-observability.md) [wiki](inference-runtime-infrastructure.md) [raw](../../raw/links/langfuse-rag-observability-official-docs-20260707.md)

# Coverage Use

Use this page as source-backed coverage for:

- `data-rag-vector`: ingestion and transform jobs, Kafka connector and stream-processor boundaries, checkpointed refresh workflows, workflow schedulers, embedding workers, metadata lineage, object-store table lifecycle controls, and production RAG tracing/evaluation.
- `eval-observability-reliability`: only where Langfuse trace/evaluation evidence explains retrieval quality or RAG feedback loops; this page does not replace broader observability, SLO, incident, or benchmark infrastructure coverage.
- `orchestration-scheduling`: only where Ray Data, Flink, Airflow, Dagster, or Prefect explain data-pipeline execution boundaries; this page does not replace Ray cluster, Kubernetes-native job queues, GPU scheduling, or cluster admission coverage.

Remaining gaps include source-to-vector deletion and retention propagation evidence, embedding model/version drift policies, retrieval-quality alerting, RAG access policy and PII controls, and production incident evidence for RAG pipelines.

# Citations

- [Ray Data pipeline source note](../../raw/links/ray-data-pipeline-official-docs-20260707.md)
- [Apache Flink stateful stream-processing source note](../../raw/links/apache-flink-stateful-stream-processing-official-docs-20260707.md)
- [Hugging Face TEI source note](../../raw/links/huggingface-text-embeddings-inference-official-docs-20260707.md)
- [DataHub and OpenLineage metadata-lineage source note](../../raw/links/datahub-openlineage-metadata-lineage-official-docs-20260707.md)
- [Langfuse RAG observability source note](../../raw/links/langfuse-rag-observability-official-docs-20260707.md)
- [Kafka Connect and Streams source note](../../raw/links/kafka-connect-streams-official-docs-20260707.md)
- [Apache Airflow workflow scheduling source note](../../raw/links/apache-airflow-workflow-scheduling-official-docs-20260707.md)
- [Dagster assets and runs source note](../../raw/links/dagster-assets-runs-official-docs-20260707.md)
- [Prefect flow/task/deployment source note](../../raw/links/prefect-flow-task-scheduling-official-docs-20260707.md)
- [Apache Iceberg table-format source note](../../raw/links/apache-iceberg-table-governance-official-docs-20260707.md)
- [Delta Lake table lifecycle source note](../../raw/links/delta-lake-table-lifecycle-official-docs-20260707.md)
- [Apache Hudi table lifecycle source note](../../raw/links/apache-hudi-table-lifecycle-official-docs-20260707.md)
- [Data RAG Vector Infrastructure](data-rag-vector-infrastructure.md)
