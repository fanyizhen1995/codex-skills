---
type: RawSource
title: Weaviate Vector Indexing Documentation
source_kind: web
url: https://docs.weaviate.io/weaviate/concepts/vector-index
captured: 2026-07-07
status: ingested
---
# Source

Official Weaviate documentation page: https://docs.weaviate.io/weaviate/concepts/vector-index

Captured as a concise source note for `ai_infra` data/RAG/vector infrastructure coverage. The full external page was not mirrored; the durable facts below are paraphrased from the official source.

# Captured Facts

- Weaviate describes vector indexing as a core vector-database component for organizing vector embeddings and improving similarity-search performance.
- The page identifies several vector index types: HNSW, flat, dynamic, and HFresh.
- HNSW is described as slower to build but suitable for larger datasets with logarithmic query-time behavior.
- The flat index is a simple lightweight index for small datasets; it uses less memory but search time grows linearly with the number of data objects.
- The dynamic index can start as flat and switch to HNSW when object count passes a threshold. The page says the default threshold is 10,000 objects, requires asynchronous indexing, and the switch is one-way.
- Weaviate's HNSW implementation builds layers that support approximate nearest-neighbor search by traversing from higher layers toward lower layers.
- The HNSW index is in memory: graph nodes and graph edges are stored in memory, so memory use grows with vector count and connection count.
- The page identifies quantization and HFresh as options to reduce memory pressure. HFresh keeps most data on disk while keeping a compressed centroid index in memory.

# Use In Wiki

Use this source note for vector index lifecycle and capacity-planning claims about Weaviate HNSW, flat, dynamic, HFresh, asynchronous indexing, memory footprint, and tenant/small-collection tradeoffs.
