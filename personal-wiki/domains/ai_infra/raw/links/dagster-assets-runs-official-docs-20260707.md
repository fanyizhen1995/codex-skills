---
type: RawSource
title: Dagster Assets And Runs Documentation
source_kind: web
url: https://docs.dagster.io/guides/build/assets/
secondary_urls:
  - https://docs.dagster.io/guides/build/jobs/
  - https://docs.dagster.io/guides/operate/schedules/
captured: 2026-07-07
status: ingested
---
# Source

Official Dagster assets documentation: https://docs.dagster.io/guides/build/assets/

Official Dagster jobs documentation: https://docs.dagster.io/guides/build/jobs/

Official Dagster schedules documentation: https://docs.dagster.io/guides/operate/schedules/

Captured as a concise source note for `ai_infra` asset-aware data workflow coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- Dagster models data products as software-defined assets, where each asset can describe data produced by computation.
- Asset dependencies encode upstream and downstream relationships between produced datasets or artifacts.
- Dagster jobs define executable selections of assets or operations, and runs are executions of those jobs.
- Dagster schedules can launch jobs on a time-based cadence, while sensors can react to external events or asset conditions.
- Dagster asset materialization metadata is useful for data-pipeline observability, but it is not a substitute for a lakehouse table transaction log or a vector-store index lifecycle.

# Use In Wiki

Use this source note for asset-oriented orchestration claims: data assets, asset dependency graphs, materialization, jobs, runs, schedules, and sensors. Pair it with DataHub/OpenLineage for portable lineage metadata and table-format sources for snapshot, delete, and retention semantics.
