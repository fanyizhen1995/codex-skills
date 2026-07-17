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
  - ../../raw/links/source-to-vector-deletion-retention-official-sources-20260707.md
  - ../../raw/links/rag-access-policy-pii-governance-official-sources-20260707.md
  - ../../raw/links/rag-propagation-drift-alert-cost-evidence-20260707.md
  - data-rag-vector-infrastructure.md
  - ../../raw/crawler/nccl-nvidia-blog-wide/20260705T041056438015Z-developer-nvidia-com-blog-designing-gpu-accelerated-query-engines-with-nvidia-gqe-ae88d57da8.md
  - ../../raw/crawler/nccl-aws-ml-blog/manifest-20260712-agentcore-mcp.json
  - ../../raw/crawler/nccl-aws-ml-blog/20260712T041317574776Z-aws-amazon-com-blogs-machine-learning-building-and-connecting-a-production-ready-ecommerce-e010a606a1.md
updated: 2026-07-17
related:
  - ai-infra-coverage-map.md
  - data-rag-vector-infrastructure.md
  - inference-runtime-infrastructure.md
---
# Summary

This page extends the `data-rag-vector` layer beyond vector database and index mechanics. It covers the pipeline surfaces around retrieval systems: data ingestion and transforms, streaming refresh, workflow orchestration, embedding workers, metadata lineage, table-format lifecycle governance, and RAG observability.

The selected sources are deliberately bounded. Ray Data supplies batch and object-store-oriented data processing evidence; Flink supplies checkpointed streaming refresh evidence; Kafka Connect and Kafka Streams supply connector and stream-processor boundaries; Airflow, Dagster, and Prefect supply workflow scheduler evidence; Hugging Face Text Embeddings Inference supplies an embedding-serving boundary; DataHub and OpenLineage supply metadata and lineage boundaries; Iceberg, Delta Lake, and Hudi supply object-store table lifecycle evidence; Azure AI Search supplies document-level access-control, chunk-level permission projection, PII masking, and blob delete-detection evidence; Langfuse supplies RAG trace, evaluation, and dataset-versioning evidence; NVIDIA GQE supplies a GPU query-engine data-path example for SQL plan ingestion, CPU-to-GPU transfer orchestration, compression, and partition pruning. Vector store internals remain in [Data RAG Vector Infrastructure](data-rag-vector-infrastructure.md).

The r10 RAG operations probe records a negative boundary: local evidence and bounded shell probes did not surface a source-backed run tying source deletes or permission changes to embedding ids, vector/search index updates, RAG cache invalidation, evaluation dataset handling, timing, and verification. Treat the run-level propagation gap as blocked-source evidence until a primary run, audit, incident, or case-study artifact is captured. [raw](../../raw/links/rag-propagation-drift-alert-cost-evidence-20260707.md)

# Pipeline Boundaries

RAG data infrastructure should be treated as a pipeline, not only as a vector index. A durable system needs source-backed control points across ingestion, refresh, orchestration, embedding, metadata, table lifecycle, and observability:

- `source ingestion and transforms`: Ray Data documents distributed reads, dataset transforms, batch inference, object-store examples, and worker resource controls for ML data pipelines. [raw](../../raw/links/ray-data-pipeline-official-docs-20260707.md)
- `streaming or incremental refresh`: Flink documents stateful stream processing, event-time processing, durable checkpoints, source-position recovery, and replayable sources such as Kafka brokers. Kafka Connect adds source/sink connector, task, worker, and Kafka-backed offset/status/config boundaries, while Kafka Streams adds processor topologies, local state stores, and changelog-backed recovery. [raw](../../raw/links/apache-flink-stateful-stream-processing-official-docs-20260707.md) [raw](../../raw/links/kafka-connect-streams-official-docs-20260707.md)
- `workflow orchestration`: Airflow DAGs and tasks, Dagster assets/jobs/runs, and Prefect flows/tasks/deployments give source-backed execution boundaries for scheduled or event-driven refresh workflows. [raw](../../raw/links/apache-airflow-workflow-scheduling-official-docs-20260707.md) [raw](../../raw/links/dagster-assets-runs-official-docs-20260707.md) [raw](../../raw/links/prefect-flow-task-scheduling-official-docs-20260707.md)
- `embedding generation`: Hugging Face Text Embeddings Inference documents an embedding-serving process with HTTP APIs, CPU/GPU images, model/revision choices, request queuing, token and batch limits, health, and Prometheus metrics. [raw](../../raw/links/huggingface-text-embeddings-inference-official-docs-20260707.md)
- `metadata and lineage`: DataHub ingestion recipes and OpenLineage run/job/dataset events provide a catalog and event envelope for recording which sources, jobs, and datasets produced embedding or retrieval artifacts. [raw](../../raw/links/datahub-openlineage-metadata-lineage-official-docs-20260707.md)
- `table lifecycle governance`: Iceberg, Delta Lake, and Hudi add snapshot or transaction-log style table states, schema evolution, row-level delete/update/upsert surfaces, and cleanup or retention operations for object-store tables. [raw](../../raw/links/apache-iceberg-table-governance-official-docs-20260707.md) [raw](../../raw/links/delta-lake-table-lifecycle-official-docs-20260707.md) [raw](../../raw/links/apache-hudi-table-lifecycle-official-docs-20260707.md)
- `deletion and access propagation`: Azure AI Search documents source deletion detection for blob indexers, document-level access control for RAG, query-time security trimming, chunk-level permission projection, and PII detection/masking in enrichment pipelines. Milvus, Qdrant, and Weaviate document downstream vector-object delete and TTL controls. [raw](../../raw/links/source-to-vector-deletion-retention-official-sources-20260707.md) [raw](../../raw/links/rag-access-policy-pii-governance-official-sources-20260707.md)
- `evaluation dataset governance`: Langfuse datasets record evaluation inputs, expected outputs, metadata, source trace links, schema validation, and dataset versions that capture item add/update/delete/archive operations over time. [raw](../../raw/links/rag-access-policy-pii-governance-official-sources-20260707.md)
- `RAG observability`: Langfuse tracing records retrieval, generation, scores, datasets, experiments, and feedback, so a RAG pipeline can connect retrieved context with model output and evaluation signals. [raw](../../raw/links/langfuse-rag-observability-official-docs-20260707.md)
- `GPU query-engine data path`: NVIDIA GQE documents a SQL query-engine data path where Apache DataFusion can produce Substrait plans, GQE maps those plans to a physical task graph, CPU-memory row groups and partitions are transferred on demand to GPU memory, and cuDF/nvCOMP/nvSHMEM-backed execution keeps compression, pruning, transfer, and GPU computation as one data-infrastructure boundary. [raw](../../raw/crawler/nccl-nvidia-blog-wide/20260705T041056438015Z-developer-nvidia-com-blog-designing-gpu-accelerated-query-engines-with-nvidia-gqe-ae88d57da8.md)

# Ingestion And Refresh

Batch ingestion and refresh jobs need dataset-level infrastructure before data reaches a vector store. Ray Data provides the source-backed batch side: it can read from file and table sources, apply dataset transformations, repartition, write outputs, and run batch inference over records. In a RAG pipeline, that maps naturally to document loading, parsing/enrichment, embedding generation, and output writes, but this page treats that as synthesis across Ray Data plus embedding-worker evidence rather than a Ray-only product claim. [raw](../../raw/links/ray-data-pipeline-official-docs-20260707.md) [raw](../../raw/links/huggingface-text-embeddings-inference-official-docs-20260707.md)

Streaming refresh has different failure boundaries. Flink's checkpoint model snapshots operator state and source positions to durable storage; recovery restores both and replays input from a rewindable source position. Kafka Connect adds a connector layer for moving external-system changes into or out of Kafka topics, with source/sink connectors split into tasks and coordinated by workers. Kafka Streams adds the application layer for processing Kafka topics through processor topologies, state stores, and changelog-backed state recovery. For RAG infrastructure, the important claim is not that every embedding refresh is exactly-once by default. The source-backed claim is narrower: a refresh pipeline can be designed around connector offsets, checkpointed state, replayable source positions, and state-store recovery so document-change processing can recover after failure without guessing where the stream stopped. This is synthesis across the Kafka and Flink sources. [raw](../../raw/links/apache-flink-stateful-stream-processing-official-docs-20260707.md) [raw](../../raw/links/kafka-connect-streams-official-docs-20260707.md)

The vector store lifecycle from the prior page remains the downstream index side. Milvus evidence already covers growing data, sealed segments, compaction, index building, and query loading; this page adds the upstream data and embedding pipeline that produces or refreshes those vectors. [wiki](data-rag-vector-infrastructure.md)

# GPU Query Engine Data Path

The local NVIDIA GQE capture is useful as data infrastructure evidence rather than model-serving or accelerator-catalog evidence. GQE is described as a GPU Query Engine reference architecture for SQL over large datasets. Its query layer accepts Substrait plans, including the source's Apache DataFusion example where SQL becomes Substrait before GQE consumes the optimized logical plan, applies GQE-specific refinements, and produces a physical plan. [raw](../../raw/crawler/nccl-nvidia-blog-wide/20260705T041056438015Z-developer-nvidia-com-blog-designing-gpu-accelerated-query-engines-with-nvidia-gqe-ae88d57da8.md)

The data-path boundary is CPU-to-GPU movement. The source says the data layer supports GPU memory, CPU memory, and disk readers, then focuses on an in-memory CPU table format where row groups contain columns and partition metadata. During transfer, the storage layer converts selected partitions into cuDF columns so the execution layer does not need to know whether compression or partition pruning was used. The execution layer builds a task graph with relational operators implemented on NVIDIA cuDF and CUDA-X dependencies including CCCL, nvCOMP, and nvSHMEM. [raw](../../raw/crawler/nccl-nvidia-blog-wide/20260705T041056438015Z-developer-nvidia-com-blog-designing-gpu-accelerated-query-engines-with-nvidia-gqe-ae88d57da8.md)

The transfer pipeline has four source-described stages for compressed, partitioned data: host-side scheduling, host-to-device transfer, GPU decompression, and CUDA kernel query computation. Compression is promoted only as a transfer and capacity mechanism: GQE uses nvCOMP for compression/decompression routines, tries LZ4 and Cascaded per column, and uses heuristics to choose between generic LZ4 and Cascaded's structured-data encoding. The NVIDIA Blackwell Decompression Engine context is source-stated as LZ77-family decompression offload that can overlap with SM kernels and copy-engine transfers, not as a standalone benchmark result in this wiki. [raw](../../raw/crawler/nccl-nvidia-blog-wide/20260705T041056438015Z-developer-nvidia-com-blog-designing-gpu-accelerated-query-engines-with-nvidia-gqe-ae88d57da8.md)

Partition pruning is the second data-movement mechanism. GQE stores partition min/max zone maps as cuDF tables in GPU memory, derives pruning expressions from SQL predicates during task graph construction, skips partitions that cannot contribute to a result, and transfers remaining discontiguous CPU partitions into contiguous GPU-side cuDF tables. The source reports 31% data skipped across TPC-H queries, 1.43x end-to-end speedup from pruning, and about 2.2 ms average zone-map evaluation overhead, but those remain NVIDIA source context. Batched `cudaMemcpyBatchAsync` is recorded as a partition-transfer overhead reduction for fine-grained partitions. [raw](../../raw/crawler/nccl-nvidia-blog-wide/20260705T041056438015Z-developer-nvidia-com-blog-designing-gpu-accelerated-query-engines-with-nvidia-gqe-ae88d57da8.md)

The benchmark paragraph must stay caveated. The source context is TPC-H SF1000 / 1 TB on a GB200 NVL4 server using one B200 GPU connected to Grace CPU by NVLink-C2C, compared with DuckDB 1.4.1 on a Turin EPYC 9755 CPU. NVIDIA reports 9.0 s total GQE runtime versus 74.0 s single-socket and 70.6 s dual-socket DuckDB, with 7.5x aggregate speedup and up to 25.5x per-query gains. The same source says the blog results are not comparable to published TPC-H results because they do not comply with the TPC-H specification; this page treats them only as source-stated benchmark context, not local reproduction, product ranking, MLCommons evidence, production SLO, or a general database-performance claim. [raw](../../raw/crawler/nccl-nvidia-blog-wide/20260705T041056438015Z-developer-nvidia-com-blog-designing-gpu-accelerated-query-engines-with-nvidia-gqe-ae88d57da8.md)

# Workflow Orchestration

Workflow schedulers are a separate control plane from stream processors and vector databases. Airflow models workflows as DAGs with tasks, dependencies, DAG runs, scheduler-created runs, task states, and retry behavior. That is useful when document parsing, embedding, index rebuild, evaluation, or cleanup happens in scheduled jobs rather than a continuously running stream. [raw](../../raw/links/apache-airflow-workflow-scheduling-official-docs-20260707.md)

Dagster and Prefect expose adjacent orchestration boundaries. Dagster's asset model makes produced datasets or artifacts first-class, with asset dependencies, jobs, runs, schedules, sensors, and materialization metadata. Prefect organizes workflows as flows with tasks, deployments, schedules, workers, and work pools. In a RAG data platform, these sources support a durable distinction: the scheduler controls when work runs and what dependencies are satisfied; it does not by itself prove that downstream vector indexes or RAG caches observed every source-table lifecycle event. [raw](../../raw/links/dagster-assets-runs-official-docs-20260707.md) [raw](../../raw/links/prefect-flow-task-scheduling-official-docs-20260707.md)

# Embedding Worker Surface

Embedding generation deserves its own serving boundary. TEI supports model id and revision selection, batch/token controls, CPU/GPU deployment variants, request queueing, health endpoints, and metrics. Those are operational controls for an embedding worker pool; they are different from vector database index parameters, even though both affect retrieval quality and latency. [raw](../../raw/links/huggingface-text-embeddings-inference-official-docs-20260707.md)

For refresh workflows, the embedding worker should be considered a versioned dependency of the data pipeline. DataHub/OpenLineage can record job, dataset, run, schema, ownership, and lineage metadata; Langfuse can record retrieval and generation traces plus evaluation scores. Together these sources support an infrastructure pattern where an embedding refresh is tied to source dataset identity, pipeline run identity, embedding model or serving revision, downstream vector index state, and observed retrieval behavior. This sentence is synthesis across the cited sources, not a claim that any single source implements the entire workflow. [raw](../../raw/links/datahub-openlineage-metadata-lineage-official-docs-20260707.md) [raw](../../raw/links/langfuse-rag-observability-official-docs-20260707.md) [raw](../../raw/links/huggingface-text-embeddings-inference-official-docs-20260707.md)

# MCP Tool Data Boundary

Parent 27 adds a narrow data-boundary example for MCP tools from the local AgentCore walkthrough. The data layer is five DynamoDB tables, Products, Customers, Orders, Reviews, and Returns, provisioned with on-demand capacity and Global Secondary Indexes for query patterns. The MCP server's `utils/dynamodb_client.py` is described as the interface for product search, order creation, review queries, and related table operations. This is application data infrastructure behind an MCP server, not generic ecommerce product guidance. [manifest](../../raw/crawler/nccl-aws-ml-blog/manifest-20260712-agentcore-mcp.json) [raw](../../raw/crawler/nccl-aws-ml-blog/20260712T041317574776Z-aws-amazon-com-blogs-machine-learning-building-and-connecting-a-production-ready-ecommerce-e010a606a1.md)

The useful data-pipeline claim is customer scoping. AgentCore Runtime validates the JWT at the infrastructure layer, the application retrieves the Cognito `custom:customer_id`, and authenticated tools use that customer identity to query only that user's orders, reviews, and returns. Before mutations, the source recommends verifying data ownership, such as matching `order.customer_id` to the token's customer id. This is a tool-data boundary for an agent/MCP workload; it does not prove source-to-vector propagation, RAG cache invalidation, evaluation dataset cleanup, or production policy enforcement. [raw](../../raw/crawler/nccl-aws-ml-blog/20260712T041317574776Z-aws-amazon-com-blogs-machine-learning-building-and-connecting-a-production-ready-ecommerce-e010a606a1.md)

# Metadata Governance

Metadata governance is the piece that keeps RAG data pipelines auditable. DataHub ingestion recipes define sources, transformers, and sinks, while OpenLineage standardizes events around jobs, runs, datasets, and facets. Those boundaries can identify which source collection, pipeline job, and produced dataset fed a vector index or evaluation dataset. [raw](../../raw/links/datahub-openlineage-metadata-lineage-official-docs-20260707.md)

Table formats add lifecycle semantics below the scheduler and above raw object-store files. Iceberg uses metadata and snapshots for consistent table states, schema and partition evolution, row-level update/delete support through engines, snapshot expiration, and orphan-file cleanup. Delta Lake uses a transaction log for table versions and metadata, DML operations such as delete/update/merge, schema enforcement/evolution, time travel, and VACUUM retention. Hudi uses table types, a timeline of actions, upsert/delete semantics, schema evolution, compaction, cleaning, and retention policies. These are source-backed table lifecycle controls, not a guarantee that embeddings or vector indexes are automatically deleted. [raw](../../raw/links/apache-iceberg-table-governance-official-docs-20260707.md) [raw](../../raw/links/delta-lake-table-lifecycle-official-docs-20260707.md) [raw](../../raw/links/apache-hudi-table-lifecycle-official-docs-20260707.md)

Search-index deletion detection is now a bounded bridge between source lifecycle and retrieval indexes. Azure AI Search indexers can detect changed blobs through timestamps, but deletion detection requires native blob soft delete or custom metadata; for custom metadata, source content is flagged first, the indexer removes the indexed document, and only then should the source file be physically deleted. The same source warns that deletion detection must be configured from the first indexer run and does not cover every one-to-many indexing case. [raw](../../raw/links/source-to-vector-deletion-retention-official-sources-20260707.md)

The access-policy source is similarly useful but narrow. Azure AI Search document-level access control for RAG stores ACL/RBAC/sensitivity metadata with indexed documents, projects permission fields into chunked indexes, and enforces query-time security trimming by matching caller claims against those fields. That supports infrastructure claims about retrieval-time authorization and chunk-level permission projection. It does not prove every source permission change is immediately reflected; the documentation separates permission synchronization from query-time enforcement. [raw](../../raw/links/rag-access-policy-pii-governance-official-sources-20260707.md)

PII controls belong in the indexing pipeline rather than only in application policy. Azure AI Search PII Detection skill can extract and mask personal-information entities during enrichment, and Azure Language PII APIs return redacted output and entity metadata. DataHub policies add catalog-side governance over who can view or change metadata resources, while Langfuse dataset versioning records evaluation item add/update/delete/archive operations so experiments can be tied to a dataset version. These sources support governance hooks around RAG data and evaluation data, not legal-compliance completion. [raw](../../raw/links/rag-access-policy-pii-governance-official-sources-20260707.md) [raw](../../raw/links/datahub-openlineage-metadata-lineage-official-docs-20260707.md)

This page should not overstate governance coverage. The local source set now supports ingestion, workflow orchestration, lineage, catalog policy, schema/ownership, run/dataset metadata, table snapshots or transaction logs, table delete/update/upsert surfaces, table cleanup/retention mechanics, search-index deletion detection, document-level RAG access metadata, chunk-level permission projection, PII masking, vector delete/TTL controls, and evaluation dataset versioning. It does not yet prove complete propagation from source-table deletes or permission changes into every embedding store, vector index, cache, and evaluation dataset in a production incident or run log.

The r10 probe strengthens that caution rather than closing the gap. It found duplicate local coverage for component-level controls and recorded DNS-blocked probes for adjacent LangSmith, Langfuse, Ragas, Grafana, and OpenCost source families, but did not capture run-level propagation, embedding-drift policy, retrieval-quality alert routing, or RAG cost-reporting output. [raw](../../raw/links/rag-propagation-drift-alert-cost-evidence-20260707.md)

# RAG Observability

RAG observability needs retrieval-level traces, not only model-server health. Langfuse documents hierarchical traces with retrieval steps, model generations, scores, datasets, experiments, user feedback, and OpenTelemetry ingestion. That supports an operator view where retrieval context, generated answers, feedback, and evaluation scores can be inspected together after an ingestion or embedding refresh. [raw](../../raw/links/langfuse-rag-observability-official-docs-20260707.md)

This page should also keep RAG observability separate from the existing NCCL and inference-runtime observability pages. NCCL technical-blog evidence covers GPU communication, fabric telemetry, Prometheus/Grafana, and RAS; inference-runtime evidence covers health or metrics surfaces for serving systems. Langfuse covers application/RAG traces and evaluation signals. These are adjacent layers, not duplicates. [wiki](nccl-technical-blog-network-observability.md) [wiki](inference-runtime-infrastructure.md) [raw](../../raw/links/langfuse-rag-observability-official-docs-20260707.md)

# Coverage Use

Use this page as source-backed coverage for:

- `data-rag-vector`: ingestion and transform jobs, Kafka connector and stream-processor boundaries, checkpointed refresh workflows, workflow schedulers, embedding workers, metadata lineage, object-store table lifecycle controls, source deletion-detection hooks, RAG document access metadata, chunk permission projection, PII masking, evaluation dataset versioning, production RAG tracing/evaluation, source-scoped DynamoDB customer-data boundaries behind MCP tools where those boundaries explain agent data access rather than RAG propagation, and GPU query-engine data-path evidence where CPU-to-GPU movement, compression, partition pruning, and query-plan ingestion explain data platform infrastructure.
- `eval-observability-reliability`: only where Langfuse trace/evaluation evidence explains retrieval quality or RAG feedback loops; this page does not replace broader observability, SLO, incident, or benchmark infrastructure coverage.
- `orchestration-scheduling`: only where Ray Data, Flink, Airflow, Dagster, or Prefect explain data-pipeline execution boundaries; this page does not replace Ray cluster, Kubernetes-native job queues, GPU scheduling, or cluster admission coverage.

Remaining gaps include full source-to-vector propagation run evidence across every store/cache/evaluation dataset, embedding model/version drift policies, retrieval-quality alerting, cost attribution, and production incident evidence for RAG pipelines.

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
- [Source-to-vector deletion and retention source note](../../raw/links/source-to-vector-deletion-retention-official-sources-20260707.md)
- [RAG access policy, PII, and evaluation governance source note](../../raw/links/rag-access-policy-pii-governance-official-sources-20260707.md)
- [RAG propagation, drift, alerting, and cost evidence probe](../../raw/links/rag-propagation-drift-alert-cost-evidence-20260707.md)
- [Data RAG Vector Infrastructure](data-rag-vector-infrastructure.md)
- [NVIDIA GQE query-engine capture](../../raw/crawler/nccl-nvidia-blog-wide/20260705T041056438015Z-developer-nvidia-com-blog-designing-gpu-accelerated-query-engines-with-nvidia-gqe-ae88d57da8.md)

- [AgentCore MCP raw manifest](../../raw/crawler/nccl-aws-ml-blog/manifest-20260712-agentcore-mcp.json)
- [AgentCore MCP AWS ML Blog capture](../../raw/crawler/nccl-aws-ml-blog/20260712T041317574776Z-aws-amazon-com-blogs-machine-learning-building-and-connecting-a-production-ready-ecommerce-e010a606a1.md)
