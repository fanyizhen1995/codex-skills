---
type: RawSource
title: pgvector README
source_kind: web
url: https://github.com/pgvector/pgvector
captured: 2026-07-07
status: ingested
---
# Source

Official pgvector GitHub repository README: https://github.com/pgvector/pgvector

Captured as a concise source note for `ai_infra` data/RAG/vector infrastructure coverage. The full external page was not mirrored; the durable facts below are paraphrased from the official source.

# Captured Facts

- pgvector describes itself as open-source vector similarity search for Postgres.
- The README positions pgvector as storing vectors alongside relational data, while retaining Postgres properties and features such as ACID behavior, point-in-time recovery, and joins.
- Supported search modes include exact and approximate nearest-neighbor search.
- Supported vector storage forms include single-precision, half-precision, binary, and sparse vectors.
- The README lists L2 distance, inner product, cosine distance, L1 distance, Hamming distance, and Jaccard distance.
- Basic usage enables the `vector` extension, adds vector columns, inserts vectors, and queries nearest neighbors with `ORDER BY` distance operators and `LIMIT`.
- By default, pgvector performs exact nearest-neighbor search. Approximate indexing can improve speed while trading away some recall.
- The supported approximate index types are HNSW and IVFFlat.
- HNSW creates a multilayer graph, has better speed/recall query behavior than IVFFlat, but takes longer to build and uses more memory. It can be created before data is loaded because it does not have an IVFFlat-style training step.
- IVFFlat divides vectors into lists, searches a subset of lists closest to the query vector, builds faster and uses less memory than HNSW, but has lower speed/recall query behavior.
- Filtering can interact with approximate indexes because filtering is applied after the approximate index scan. The README discusses iterative index scans and ordinary Postgres indexes, partial indexes, or partitioning as options for filtered nearest-neighbor queries.

# Use In Wiki

Use this source note for PostgreSQL-native vector retrieval claims about pgvector storage, distance operators, exact search default, HNSW and IVFFlat approximate indexes, filtering behavior, and relational integration.
