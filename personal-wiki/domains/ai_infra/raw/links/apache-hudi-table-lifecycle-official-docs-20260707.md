---
type: RawSource
title: Apache Hudi Table Lifecycle Documentation
source_kind: web
url: https://hudi.apache.org/docs/overview/
secondary_urls:
  - https://hudi.apache.org/docs/table_types/
  - https://hudi.apache.org/docs/schema_evolution/
  - https://hudi.apache.org/docs/cleaning/
captured: 2026-07-07
status: ingested
---
# Source

Official Apache Hudi overview documentation: https://hudi.apache.org/docs/overview/

Official Apache Hudi table types documentation: https://hudi.apache.org/docs/table_types/

Official Apache Hudi schema evolution documentation: https://hudi.apache.org/docs/schema_evolution/

Official Apache Hudi cleaning documentation: https://hudi.apache.org/docs/cleaning/

Captured as a concise source note for `ai_infra` table-format lifecycle coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- Apache Hudi is a data lakehouse platform and table format for managing large analytic datasets on file/object storage.
- Hudi supports copy-on-write and merge-on-read table types, which separate physical write layout and query/read behavior.
- Hudi tables maintain a timeline of actions such as commits, delta commits, compaction, cleaning, and rollback.
- Hudi supports upsert and delete semantics at the table layer instead of requiring a full table rewrite for every record-level change.
- Hudi supports schema evolution, subject to compatibility rules between incoming records and stored table schema.
- Hudi cleaning removes older file versions according to retention policies, making cleanup policy an explicit lifecycle boundary.

# Use In Wiki

Use this source note for Hudi claims about table types, timeline actions, upsert/delete behavior, schema evolution, compaction/cleaning, and retention policies. Do not use it to claim that a vector index or RAG cache automatically follows Hudi deletes without a designed propagation workflow.
