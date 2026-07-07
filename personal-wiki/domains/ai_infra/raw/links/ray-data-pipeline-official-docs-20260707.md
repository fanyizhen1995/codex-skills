---
type: RawSource
title: Ray Data Pipeline Documentation
source_kind: web
url: https://docs.ray.io/en/latest/data/data.html
captured: 2026-07-07
status: ingested
---
# Source

Official Ray Data documentation: https://docs.ray.io/en/latest/data/data.html

Captured as a concise source note for `ai_infra` data/RAG pipeline coverage. The full external page was not mirrored; the durable facts below are paraphrased from the official source.

# Captured Facts

- Ray Data is a distributed data processing library for ML workloads, with a streaming execution engine that can scale to large datasets and fit into a larger Ray application.
- The documentation positions Ray Data for data loading, preprocessing, batch inference, and model training data pipelines.
- Ray Data examples include reading from S3, applying dataset transformations, repartitioning data, writing outputs, and passing datasets into Ray Train.
- The API surface includes `read_*` methods for file and table inputs, `map`, `map_batches`, `flat_map`, `filter`, `random_shuffle`, and `write_*` output methods.
- Ray Data supports batch inference by mapping model work over batches of records, which is useful for embedding-generation or document-enrichment jobs that need to run model inference over large corpora.
- Ray Data provides stateful transforms and configurable resources for workers, so a pipeline can keep model objects or connections inside worker actors instead of reloading them for every row.
- Ray Data uses blocks and streaming execution to pipeline operators and limit memory pressure while processing datasets larger than a single machine.

# Use In Wiki

Use this source note for AI data pipeline claims about distributed dataset ingestion, object-store inputs, preprocessing transforms, batch model inference, batch embedding generation, and resource-aware data pipeline workers.
