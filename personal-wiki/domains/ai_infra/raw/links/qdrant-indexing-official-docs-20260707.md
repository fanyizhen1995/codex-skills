---
type: RawSource
title: Qdrant Indexing Documentation
source_kind: web
url: https://qdrant.tech/documentation/manage-data/indexing/
captured: 2026-07-07
status: ingested
---
# Source

Official Qdrant documentation page: https://qdrant.tech/documentation/manage-data/indexing/

Captured as a concise source note for `ai_infra` data/RAG/vector infrastructure coverage. The full external page was not mirrored; the durable facts below are paraphrased from the official source.

# Captured Facts

- Qdrant frames indexing as a combination of vector indexes and traditional/payload indexes: vector indexes accelerate vector search, while payload indexes accelerate filtering.
- Segment indexes exist independently, while index parameters are configured at the collection level.
- Qdrant currently uses HNSW as its dense vector index.
- Qdrant recommends creating payload indexes before ingesting data so filterable HNSW can generate additional edges that use indexed payload values.
- Filterable HNSW addresses filtered search cases where neither a payload index with full rescoring nor a plain HNSW graph is sufficient; Qdrant adds graph edges based on indexed payload values to search nearby vectors while applying filters during graph traversal.
- Payload indexes are memory resident by default for low-latency search access, but selected payload indexes can be configured on disk when they are large or rarely used, with possible cold-query latency impact.
- Qdrant supports full-text search over string payloads with tokenization options and phrase-search configuration.
- Qdrant supports sparse vector indexing. Sparse vectors are indexed with a structure optimized for high-zero vectors, similar to an inverted index; the sparse index is exact, immediately indexes mutable sparse vectors, and can be useful when collections store both dense and sparse vectors.
- Sparse vector indexes can be configured as in-memory or on-disk, and sparse vectors do not need a predefined vector size.

# Use In Wiki

Use this source note for vector retrieval infrastructure claims about Qdrant dense HNSW, payload indexes, filter-aware graph edges, full-text payload indexing, sparse vector indexing, and memory/disk placement tradeoffs.
