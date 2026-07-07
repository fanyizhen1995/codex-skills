---
type: Reference
title: Data RAG Vector Infrastructure
description: Source-backed reference for vector database, retrieval, and embedding-index infrastructure across Milvus, Qdrant, Weaviate, pgvector, and FAISS.
domain: ai_infra
status: reviewed
aliases:
  - vector database infrastructure
  - RAG vector infrastructure
  - embedding retrieval infrastructure
tags:
  - data-rag-vector
  - vector-database
  - rag
  - retrieval
  - indexing
source_refs:
  - ../../raw/links/milvus-architecture-overview-20260707.md
  - ../../raw/links/qdrant-indexing-official-docs-20260707.md
  - ../../raw/links/weaviate-vector-indexing-official-docs-20260707.md
  - ../../raw/links/pgvector-readme-official-20260707.md
  - ../../raw/links/faiss-readme-and-indexes-official-20260707.md
  - ../../raw/links/source-to-vector-deletion-retention-official-sources-20260707.md
updated: 2026-07-07
related:
  - ai-infra-coverage-map.md
  - data-rag-pipeline-infrastructure.md
  - ../papers/hitchhikers-guide-agentic-ai.md
---
# Summary

This reference closes the first primary-source gap for the `data-rag-vector` layer. It covers vector database architecture and retrieval-index behavior using official source notes for Milvus, Qdrant, Weaviate, pgvector, and FAISS, and now adds bounded vector-store deletion and retention controls. The Hitchhiker paper remains useful for high-level RAG and memory context, but the operational facts here come from system-specific primary sources.

# Vector Database Architecture

Milvus is the clearest distributed vector database architecture source in this round. Its official architecture page describes a cloud-native vector database with disaggregated storage and compute, a stateless proxy access layer, a single active Coordinator, stateless worker nodes, metadata storage, object storage, and WAL storage. Search requests flow through proxies to Streaming Nodes and Query Nodes, then results are reduced across nodes before the client receives final results. Insert requests are logged to WAL storage, processed as growing data, sealed into historical segments, compacted and indexed by Data Nodes, then loaded by Query Nodes. [raw](../../raw/links/milvus-architecture-overview-20260707.md)

Qdrant and Weaviate emphasize different operational cuts of the same retrieval layer. Qdrant documents segment-level indexes with collection-level parameters and combines dense vector indexes with payload indexes so vector search and filtering can cooperate. Weaviate documents index selection across HNSW, flat, dynamic, and HFresh indexes, which makes memory footprint and collection size first-class capacity choices. [raw](../../raw/links/qdrant-indexing-official-docs-20260707.md) [raw](../../raw/links/weaviate-vector-indexing-official-docs-20260707.md)

pgvector is the relational-storage variant in this source set. Its README positions vectors as stored alongside normal Postgres data while retaining Postgres features such as joins, recovery, and ordinary client access. That makes it useful coverage for RAG systems that need vector retrieval without separating embeddings from transactional or metadata tables. [raw](../../raw/links/pgvector-readme-official-20260707.md)

# Index And Search Tradeoffs

HNSW is the common approximate-nearest-neighbor index surface across Qdrant, Weaviate, and pgvector. Qdrant currently uses HNSW as its dense vector index; Weaviate describes HNSW as a layered in-memory graph; pgvector documents HNSW as a multilayer graph with better query speed/recall behavior than IVFFlat but slower build time and higher memory use. [raw](../../raw/links/qdrant-indexing-official-docs-20260707.md) [raw](../../raw/links/weaviate-vector-indexing-official-docs-20260707.md) [raw](../../raw/links/pgvector-readme-official-20260707.md)

The planner should treat vector retrieval claims as tradeoff claims, not universal performance claims. pgvector defaults to exact nearest-neighbor search and documents HNSW and IVFFlat as approximate indexes that trade recall for speed. FAISS makes that tradeoff explicit across many index families: exact flat indexes, HNSW, inverted-file indexes, scalar and product quantizers, and IVF plus product quantization. Its README frames the core selection dimensions as search time, search quality, memory per vector, training time, adding time, and whether external training data is needed. [raw](../../raw/links/pgvector-readme-official-20260707.md) [raw](../../raw/links/faiss-readme-and-indexes-official-20260707.md)

FAISS is library infrastructure rather than a database service, but it is still primary AI-infra evidence because Milvus cites FAISS as one of the vector search libraries it builds on, and FAISS itself documents CPU/GPU dense-vector similarity search with multiple index families. Use it to explain index algorithm tradeoffs, not database clustering, WAL, or query-routing behavior. [raw](../../raw/links/milvus-architecture-overview-20260707.md) [raw](../../raw/links/faiss-readme-and-indexes-official-20260707.md)

# Filtering, Sparse Retrieval, And Hybrid Search

Filtered retrieval is not just a SQL `WHERE` clause attached to ANN. Qdrant documents why payload indexes and vector indexes alone do not fully solve filtered search, then describes filterable HNSW edges based on indexed payload values. It recommends creating payload indexes before ingesting data so the filter-aware graph can be generated during indexing. [raw](../../raw/links/qdrant-indexing-official-docs-20260707.md)

pgvector records a related operational caveat: with approximate indexes, filtering is applied after the index scan, so filtered nearest-neighbor queries may need iterative scans, ordinary Postgres indexes, partial indexes, or partitioning. [raw](../../raw/links/pgvector-readme-official-20260707.md)

Qdrant also provides the clearest source-backed sparse retrieval evidence in this round. Its sparse vector index is exact, resembles an inverted index, can be configured in memory or on disk, does not require a predefined vector size, and is useful when collections store both dense and sparse vectors. Its full-text payload index adds word or phrase filtering over string payloads. [raw](../../raw/links/qdrant-indexing-official-docs-20260707.md)

# Capacity And Lifecycle Signals

Memory placement is a recurring design dimension. Weaviate says its HNSW graph stores nodes and edges in memory, with memory growth tied to vector and connection counts. It positions flat indexes for small isolated datasets, dynamic indexes for switching from flat to HNSW after a threshold, and HFresh for lower memory pressure by keeping most data on disk. [raw](../../raw/links/weaviate-vector-indexing-official-docs-20260707.md)

Qdrant exposes similar choices through in-memory versus on-disk payload and sparse-vector indexes, with a latency tradeoff for cold on-disk access. FAISS exposes memory and precision tradeoffs through compressed encodings, product quantization, and inverted-file search. [raw](../../raw/links/qdrant-indexing-official-docs-20260707.md) [raw](../../raw/links/faiss-readme-and-indexes-official-20260707.md)

Milvus contributes lifecycle evidence around ingestion and index building: growing data is made available for query, full segments become sealed historical data, Data Nodes compact and build indexes, and Query Nodes load those built indexes. This is useful when discussing embedding ingestion pipelines because the database side has a staged durability, sealing, compaction, indexing, and serving path. [raw](../../raw/links/milvus-architecture-overview-20260707.md)

# Deletion And Retention Controls

The deletion and retention source note adds direct downstream vector-store controls. Milvus documents entity deletion by filter expression, primary key, or partition and collection/entity TTL where expired entities stop appearing in search or query before physical removal happens during later compaction. Qdrant documents deleting points by explicit ids or filter selector, with operation acknowledgement and optional wait/ordering controls. Weaviate documents object deletion by id, by filter, or by multiple ids; object TTL; and tenant deletion that removes a tenant shard and its objects. [raw](../../raw/links/source-to-vector-deletion-retention-official-sources-20260707.md)

These controls prove that the vector-store side can delete or age out records. They do not prove source-to-vector propagation by themselves. A production RAG platform still has to map source document/table identity to embedding ids, run source deletion detection, delete or expire derived vector records, invalidate caches, and decide how evaluation datasets treat old examples. That broader chain is synthesis across vector-store, pipeline, search-index, catalog, and evaluation sources, not a single-source guarantee. [raw](../../raw/links/source-to-vector-deletion-retention-official-sources-20260707.md) [wiki](data-rag-pipeline-infrastructure.md)

# Coverage Use

Use this page as source-backed coverage for:

- `data-rag-vector`: vector database architecture, vector index tradeoffs, filtered retrieval, sparse retrieval, full-text payload indexing, embedding-index lifecycle, vector-object deletion, vector-store TTL, and tenant-scoped vector data deletion.
- `network-storage-cluster`: only when explaining vector database storage/WAL/object-store dependencies; this page does not replace cluster network or parallel filesystem coverage.
- `eval-observability-reliability`: only when explaining retrieval correctness and recall/speed tradeoffs; this page does not replace evaluation or observability tooling coverage.

For ingestion, embedding worker, Kafka-style streaming, workflow scheduling, table-format lifecycle, metadata lineage, document ACL propagation, PII masking, evaluation-dataset versioning, and RAG observability coverage beyond vector index mechanics, use [Data RAG Pipeline Infrastructure](data-rag-pipeline-infrastructure.md). Remaining gaps after that page include full end-to-end deletion propagation across every source, vector store, cache, and evaluation dataset; embedding model drift policy; retrieval-quality alerting; cost attribution; and production incident evidence.

# Citations

- [Milvus architecture source note](../../raw/links/milvus-architecture-overview-20260707.md)
- [Qdrant indexing source note](../../raw/links/qdrant-indexing-official-docs-20260707.md)
- [Weaviate vector indexing source note](../../raw/links/weaviate-vector-indexing-official-docs-20260707.md)
- [pgvector README source note](../../raw/links/pgvector-readme-official-20260707.md)
- [FAISS README and indexes source note](../../raw/links/faiss-readme-and-indexes-official-20260707.md)
- [Source-to-vector deletion and retention source note](../../raw/links/source-to-vector-deletion-retention-official-sources-20260707.md)
