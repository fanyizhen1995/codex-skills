---
type: RawSource
title: Kubernetes And Kueue Quota Governance Documentation
source_kind: web
url: https://kubernetes.io/docs/concepts/policy/resource-quotas/
related_urls:
  - https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/
  - https://kueue.sigs.k8s.io/docs/concepts/resource_flavor/
captured: 2026-07-07
status: ingested
---
# Source

Official Kubernetes and Kueue documentation:

- Kubernetes Resource Quotas: https://kubernetes.io/docs/concepts/policy/resource-quotas/
- Kueue ClusterQueue concept: https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/
- Kueue ResourceFlavor concept: https://kueue.sigs.k8s.io/docs/concepts/resource_flavor/

Captured as a concise source note for `ai_infra` quota-governance coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- Kubernetes ResourceQuota constrains aggregate resource consumption within a namespace.
- ResourceQuota can limit compute resources, storage resources, and object counts; quota enforcement is namespace-scoped.
- Kubernetes quota is a baseline namespace governance mechanism, but it does not by itself express batch-workload queueing, borrowing, or resource-flavor placement rules.
- Kueue ClusterQueue is the resource-pool and admission-governance object used to decide whether queued workloads can be admitted.
- ClusterQueue quota is organized by covered resources and resource flavors, which lets operators express quota separately for different node, accelerator, or capacity classes.
- Kueue cohorts allow ClusterQueues to share quota under configured borrowing and lending rules.
- Kueue ResourceFlavor describes resource variations such as node labels, taints, or topology/capacity classes, making it a useful abstraction for GPU family, reservation, or placement governance.

# Use In Wiki

Use this source note for quota-governance claims about namespace-level ResourceQuota, Kueue admission control, ClusterQueue quota, cohorts, borrowing/lending, and ResourceFlavor-based accelerator placement boundaries.
