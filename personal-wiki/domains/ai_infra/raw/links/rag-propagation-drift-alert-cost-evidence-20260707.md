---
type: RawSource
title: RAG Propagation Drift Alert Cost Evidence Probe
source_kind: web-link-probe-note
url: https://docs.smith.langchain.com/evaluation
related_urls:
  - https://langfuse.com/docs/scores/overview
  - https://docs.ragas.io/en/stable/howtos/applications/monitoring/
  - https://grafana.com/docs/grafana-cloud/monitor-infrastructure/integrations/integration-reference/integration-llm/
  - https://opencost.io/docs/integrations/opencost-and-kubecost/
captured: 2026-07-07
status: blocked
---
# Source

Bounded source-probe note for the `ai_infra` data/RAG operations gap:

- full source-to-vector/cache/evaluation-dataset deletion or permission propagation run evidence;
- embedding model/version drift policy with rebuild or backfill controls and retrieval validation;
- retrieval-quality alerting with thresholds, routes, owners, and observed RAG runs;
- RAG cost-attribution reporting that joins pipeline, embedding, vector/search, cache/serving, Kubernetes/cloud labels, and team ownership.

This task intentionally did not promote a new end-to-end propagation, drift, retrieval-alert, or RAG chargeback claim. Existing local notes already cover component mechanics, but the remaining gap requires a run, audit, incident, or case-study artifact that ties multiple components together.

# Local Duplicate Search

Local search covered `wiki/`, `raw/links/`, `raw/crawler/`, `raw/github/`, `coverage-map.json`, `loop-state.json`, `ingest.md`, the r7 RAG governance gap proof, and the r8 policy/chargeback gap proof for:

- `source-to-vector`
- `deletion propagation`
- `retention propagation`
- `permission change`
- `embedding id`
- `vector index`
- `search index`
- `RAG cache`
- `evaluation dataset`
- `Langfuse dataset version`
- `DataHub lineage`
- `OpenLineage run`
- `Azure AI Search deletion detection`
- `Milvus`
- `Qdrant`
- `Weaviate`
- `embedding model version`
- `embedding drift`
- `retrieval-quality alert`
- `retrieval quality score`
- `Ragas`
- `Phoenix`
- `LangSmith`
- `OpenTelemetry GenAI`
- `Grafana AI Observability`
- `OpenCost`
- `cost attribution`
- `duplicate boundary`
- `blocked-source`
- `run evidence`

Findings:

- Existing local RAG evidence already covers vector-store object deletion, vector TTL, tenant deletion, Azure AI Search source deletion detection, document-level access metadata, query-time security trimming, chunk permission projection, PII masking, DataHub policy, Weaviate RBAC/tenancy, Langfuse dataset versioning, DataHub/OpenLineage lineage envelopes, Langfuse RAG traces, LangSmith/Phoenix/Ragas evaluation mechanics, OpenTelemetry GenAI retrieval semantics, Grafana AI Observability metric/alert examples, OpenCost allocation APIs, and cross-cloud cost-allocation dimensions.
- Existing curated pages explicitly keep the full source-to-vector/cache/evaluation propagation, embedding drift policy, retrieval-quality alerting, RAG cost-attribution run, production incident, and evaluation dataset audit-run boundaries open.
- No local raw or curated file ties a source delete, permission change, or retention event to embedding ids, vector/search index updates, RAG cache invalidation, evaluation dataset handling, timing, and verification in one run.
- No local raw or curated file records an embedding model/version drift policy that includes old/new embedding compatibility, rebuild or backfill triggers, index state transitions, and retrieval-quality validation.
- No local raw or curated file records a retrieval-quality alert with a concrete threshold, notification route, owner, and observed RAG production or staging run.
- No local raw or curated file records RAG cost attribution that joins pipeline jobs, embedding workers, vector/search resources, cache or serving costs, Kubernetes/cloud labels, and team ownership into a reporting output.

# Link Probe

Local shell probes were bounded to source families adjacent to the existing local evidence:

- `https://docs.smith.langchain.com/evaluation`
- `https://langfuse.com/docs/scores/overview`
- `https://docs.ragas.io/en/stable/howtos/applications/monitoring/`
- `https://grafana.com/docs/grafana-cloud/monitor-infrastructure/integrations/integration-reference/integration-llm/`
- `https://opencost.io/docs/integrations/opencost-and-kubecost/`

Result:

- The shell sandbox returned `Temporary failure in name resolution` for all selected external probes.
- Because source content was not available through local raw evidence or bounded shell probes, this task records the run-level RAG propagation/drift/alert/cost gap as blocked-source evidence rather than inferring end-to-end behavior from component documentation.

# Captured Boundary

Use this note as blocked-source evidence only:

- It proves the local corpus already has strong duplicate boundaries for component deletion, permission, lineage, tracing, evaluation, alerting, and cost mechanics.
- It proves this run attempted bounded probes for adjacent primary source families and was blocked by local DNS resolution.
- It does not prove full source-to-vector propagation, automatic cache invalidation, evaluation dataset cleanup, embedding drift policy, retrieval-quality alerting, production SLO ownership, or RAG chargeback correctness.

# Future Promotion Criteria

A future RAG operations claim can be promoted only after a specific primary source, local run artifact, audit, incident, or case study is captured and preserves the relevant boundary:

- source delete, permission-change, or retention event identity;
- source row/document/table identity mapped to embedding ids or chunk ids;
- vector index and search index update evidence;
- RAG cache invalidation or explicit no-cache boundary;
- evaluation dataset item handling and versioning;
- timing, retry, verification, and failure behavior;
- embedding model/version identity, compatibility boundary, rebuild or backfill trigger, and retrieval-quality validation;
- retrieval-quality metric, threshold, notification route, owner, and observed run;
- cost report joining pipeline jobs, embedding workers, vector/search resources, cache or serving cost, Kubernetes/cloud labels, and team ownership;
- environment, impact, remediation, and follow-up ownership for any incident or postmortem claim.
