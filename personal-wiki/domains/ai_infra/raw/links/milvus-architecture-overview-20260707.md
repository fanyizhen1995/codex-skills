---
type: RawSource
title: Milvus Architecture Overview
source_kind: web
url: https://milvus.io/docs/architecture_overview.md
captured: 2026-07-07
status: ingested
---
# Source

Official Milvus documentation page: https://milvus.io/docs/architecture_overview.md

Captured as a concise source note for `ai_infra` data/RAG/vector infrastructure coverage. The full external page was not mirrored; the durable facts below are paraphrased from the official source.

# Captured Facts

- Milvus describes itself as an open-source, cloud-native vector database for high-performance similarity search on massive vector datasets, built on vector search libraries including Faiss, HNSW, DiskANN, and SCANN.
- The architecture page presents Milvus as a modular, scalable design with disaggregated storage and compute layers.
- Milvus separates data plane and control plane responsibilities across four main layers whose scalability and disaster recovery can be handled independently.
- The access layer consists of stateless proxies that validate client requests, expose a unified service address through load-balancing components, aggregate intermediate results, and return final results to clients.
- The Coordinator maintains cluster topology, schedules tasks, manages schema/access-control operations, binds WAL and Streaming Nodes, manages query routing views, and distributes offline work such as compaction and index building.
- Worker nodes are stateless executors. Streaming Nodes handle shard-level consistency, WAL-based fault recovery, growing-data querying, query-plan generation, and conversion of growing data into sealed data. Query Nodes load historical data from object storage and serve historical queries. Data Nodes perform offline historical processing such as compaction and index building.
- Milvus storage includes meta storage, log broker/WAL storage, and object storage. The documentation names etcd for metadata, MinIO with S3 or Azure Blob deployment options for object storage, and Kafka, Pulsar, or Woodpecker as common WAL implementations.
- The search operation path routes client requests through the proxy, target Streaming Nodes, Query Nodes for sealed data, and multi-level result reduction before returning results.
- The insert path logs the operation to WAL storage, processes data in real time, converts full growing segments to sealed segments, has Data Nodes compact and build indexes, and has Query Nodes load newly built indexes.

# Use In Wiki

Use this source note for vector database architecture claims about Milvus access proxies, coordinator/worker separation, storage/WAL layers, object storage, sealed/growing data flow, and index-building lifecycle.
