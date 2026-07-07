---
type: RawSource
title: Apache Iceberg Table Format Documentation
source_kind: web
url: https://iceberg.apache.org/docs/latest/
secondary_urls:
  - https://iceberg.apache.org/docs/latest/evolution/
  - https://iceberg.apache.org/docs/latest/maintenance/
captured: 2026-07-07
status: ingested
---
# Source

Official Apache Iceberg documentation: https://iceberg.apache.org/docs/latest/

Official Apache Iceberg evolution documentation: https://iceberg.apache.org/docs/latest/evolution/

Official Apache Iceberg maintenance documentation: https://iceberg.apache.org/docs/latest/maintenance/

Captured as a concise source note for `ai_infra` object-store table-format governance coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- Apache Iceberg is an open table format for large analytic datasets.
- Iceberg tables are tracked through metadata and snapshots, so readers can choose consistent table states rather than scanning an object-store directory directly.
- Iceberg supports schema evolution and partition evolution without requiring readers to infer schema or partition behavior only from physical file paths.
- Iceberg supports row-level update and delete operations through engine integrations that write new table metadata and data/delete files.
- Iceberg maintenance operations include expiring old snapshots and removing orphan files, which are separate from normal query planning and write commits.
- Iceberg snapshot expiration and orphan-file deletion are lifecycle governance controls; they need policy decisions before RAG pipelines use old source data or derived embeddings as still-valid evidence.

# Use In Wiki

Use this source note for table-format claims about snapshots, metadata-driven table state, schema and partition evolution, row-level delete/update support, snapshot expiration, and orphan-file cleanup. Do not use it as proof that a downstream vector database automatically deletes or re-embeds documents after a table lifecycle event.
