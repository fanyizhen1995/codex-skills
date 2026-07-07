---
type: RawSource
title: DataHub Metadata Ingestion And OpenLineage
source_kind: web
url: https://docs.datahub.com/docs/metadata-ingestion/
secondary_urls:
  - https://openlineage.io/docs/
captured: 2026-07-07
status: ingested
---
# Source

Official DataHub metadata-ingestion documentation: https://docs.datahub.com/docs/metadata-ingestion/

Official OpenLineage documentation: https://openlineage.io/docs/

Captured as a concise source note for `ai_infra` metadata governance and lineage coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- DataHub describes metadata ingestion as the process of extracting metadata from external systems and pushing it into DataHub.
- DataHub supports ingestion through a CLI, scheduled ingestion, and managed ingestion sources, depending on the deployment mode.
- DataHub ingestion recipes are YAML configuration files that define a source, optional transformers, and a sink.
- DataHub source types include databases, data warehouses, BI tools, message queues, orchestration tools, and cloud/object-store systems.
- DataHub ingestion is useful to AI data pipelines because it can bring dataset, schema, lineage, ownership, and platform metadata into a central catalog rather than leaving those facts only inside pipeline code.
- OpenLineage defines an open standard for collecting lineage metadata from jobs, runs, and datasets.
- OpenLineage events carry run, job, dataset, and facet information, which provides a portable lineage envelope for systems that emit or consume lineage metadata.

# Use In Wiki

Use this source note for metadata-governance claims about ingestion recipes, catalog ingestion, source/sink boundaries, lineage event envelopes, dataset/job/run metadata, ownership/schema discovery, and freshness or lineage signals that AI data and embedding pipelines can attach to produced artifacts.
