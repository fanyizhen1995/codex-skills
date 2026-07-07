---
type: RawSource
title: OpenCost Cost Allocation Documentation
source_kind: web
url: https://opencost.io/docs/integrations/api/
related_urls:
  - https://www.opencost.io/docs/
captured: 2026-07-07
status: ingested
---
# Source

Official OpenCost documentation:

- OpenCost API documentation: https://opencost.io/docs/integrations/api/
- OpenCost documentation home: https://www.opencost.io/docs/

Captured as a concise source note for `ai_infra` cost-attribution coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- OpenCost documents APIs for querying Kubernetes cost data.
- The allocation API is the relevant interface for workload cost attribution because it reports cost over a requested time window and supports aggregation dimensions.
- OpenCost cost allocation can be used to attribute cluster spend to Kubernetes objects and organizational dimensions such as namespace, workload, pod, labels, and related grouping keys.
- OpenCost is cost-accounting evidence, not a quota or admission-control mechanism. It complements ResourceQuota and Kueue by measuring where cost landed after workloads ran.
- For AI infrastructure, OpenCost evidence is most useful when GPU, node, namespace, and workload labels are kept consistent enough to map accelerator spend back to teams or jobs.

# Use In Wiki

Use this source note for source-backed claims about Kubernetes cost allocation, workload-level attribution dimensions, and the boundary between accounting evidence and quota/admission governance.
