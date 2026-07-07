---
type: RawSource
title: Prefect Flow Task And Deployment Documentation
source_kind: web
url: https://docs.prefect.io/v3/concepts/flows
secondary_urls:
  - https://docs.prefect.io/v3/concepts/tasks
  - https://docs.prefect.io/v3/concepts/deployments
captured: 2026-07-07
status: ingested
---
# Source

Official Prefect flows documentation: https://docs.prefect.io/v3/concepts/flows

Official Prefect tasks documentation: https://docs.prefect.io/v3/concepts/tasks

Official Prefect deployments documentation: https://docs.prefect.io/v3/concepts/deployments

Captured as a concise source note for `ai_infra` workflow scheduling coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- Prefect flows are workflow entry points and organize task execution into a trackable run.
- Prefect tasks are discrete units of work inside flows and can carry operational settings such as retries, caching, and timeout behavior.
- Prefect deployments package a flow for remote or scheduled execution with configuration such as parameters, schedules, work pools, and infrastructure settings.
- Prefect workers poll work pools and execute scheduled or queued flow runs.
- Prefect provides workflow-run orchestration evidence, not table-format transaction evidence, vector-index lifecycle evidence, or RAG access-policy evidence by itself.

# Use In Wiki

Use this source note for flow/task/deployment boundaries, scheduled flow runs, workers and work pools, and retry/caching controls. Use separate metadata, table-format, and RAG evaluation sources when claims involve lineage, retention, or retrieval quality.
