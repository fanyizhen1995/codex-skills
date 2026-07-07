---
type: Reference
title: Security Governance Cost Infrastructure
description: Source-backed reference for AI platform tenant isolation, accelerator sharing governance, quota controls, cost attribution, and capacity planning.
domain: ai_infra
status: reviewed
aliases:
  - AI platform security governance cost
  - tenant isolation governance cost infrastructure
tags:
  - security
  - governance
  - cost
  - tenant-isolation
  - quota
  - capacity-planning
source_refs:
  - ../../raw/crawler/nccl-nvidia-blog-wide/20260626T015710841547Z-developer-nvidia-com-blog-one-click-multi-tenant-security-with-nvidia-quantum-infiniband-5b2cd4e1d4.md
  - ../../raw/links/nvidia-gpu-isolation-confidential-computing-official-20260707.md
  - ../../raw/links/kubernetes-kueue-quota-governance-official-20260707.md
  - ../../raw/links/opencost-cost-attribution-official-20260707.md
  - ../../raw/links/aws-accelerator-capacity-quota-planning-official-20260707.md
  - ../../raw/links/rag-access-policy-pii-governance-official-sources-20260707.md
  - ../../raw/links/cross-cloud-chargeback-policy-enforcement-official-sources-20260707.md
  - ../../raw/links/policy-enforcement-deletion-retention-audit-official-sources-20260707.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704298674Z-developer-nvidia-com-blog-memory-efficiency-faster-initialization-and-cost-estimation-with-32a1d0c118.md
  - ../../raw/crawler/compute-accelerators-nvidia-bluefield-3/20260627T153315013778Z-www-nvidia-com-en-us-networking-products-data-processing-unit-d517920f8d.md
  - ../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-summary.json
updated: 2026-07-07
related:
  - ai-infra-coverage-map.md
  - nccl-technical-blog-network-observability.md
  - compute-accelerator-parameter-comparison.md
  - ../projects/kueue.md
---
# Summary

This reference captures the security, governance, quota, cost, and capacity-planning layer for AI infrastructure. It deliberately separates seven control planes that are easy to conflate:

- tenant isolation for network and accelerator boundaries;
- quota/admission governance for namespaces, queues, and resource flavors;
- RAG access policy, PII controls, metadata policy, and evaluation dataset governance;
- cost attribution after workloads run;
- cross-cloud chargeback normalization across cloud billing records, Kubernetes labels, and team ownership;
- cloud capacity reservation and service-quota planning before workloads run;
- policy-as-code enforcement and audit reporting for resource configuration.

The layer is broader than NCCL cost-estimation evidence and broader than DPU positioning. It is still partial because local evidence now covers infrastructure controls, selected RAG governance hooks, cross-cloud chargeback dimensions, and policy/audit mechanics, but not complete chargeback parity, full end-to-end policy-enforcement run evidence, or real incident/postmortem evidence.

# Tenant Isolation And Accelerator Sharing

The local NVIDIA Quantum InfiniBand capture is direct evidence for fabric-level multi-tenant isolation. It describes UFM intent-based security profiles for General, Bare Metal Cloud, and Secured Bare Metal Cloud deployments. The multi-tenant controls include PKey isolation, MAD key protection, GUID-based access control, service-key authentication, source-based rate limiting, and Continuous Security Verification reports. This supports fabric security claims for large GPU clusters, not generic application authorization claims. [raw](../../raw/crawler/nccl-nvidia-blog-wide/20260626T015710841547Z-developer-nvidia-com-blog-one-click-multi-tenant-security-with-nvidia-quantum-infiniband-5b2cd4e1d4.md)

NVIDIA MIG and vGPU documentation fills the accelerator-sharing boundary. MIG is the hardware-partitioning model: supported GPUs can be split into GPU instances with dedicated compute and memory resources. vGPU is the virtualized profile model: a hypervisor presents configured vGPU profiles to guest VMs. Use MIG/vGPU as accelerator allocation and isolation evidence; do not infer NCCL support, topology behavior, or legal compliance from those docs alone. [source note](../../raw/links/nvidia-gpu-isolation-confidential-computing-official-20260707.md)

NVIDIA confidential-computing documentation adds a trust and attestation boundary for sensitive GPU workloads. It supports claims about protected workload operation and remote attestation, but it does not replace quota policy, admission control, or network isolation. [source note](../../raw/links/nvidia-gpu-isolation-confidential-computing-official-20260707.md)

DPU evidence remains adjacent rather than sufficient by itself. The local BlueField-3 capture supports DPU/security positioning and line-rate infrastructure offload, but this page does not use it to claim tenant policy correctness without the InfiniBand, MIG/vGPU, or quota sources above. [raw](../../raw/crawler/compute-accelerators-nvidia-bluefield-3/20260627T153315013778Z-www-nvidia-com-en-us-networking-products-data-processing-unit-d517920f8d.md)

# Quota Governance

Kubernetes ResourceQuota is the namespace-scoped baseline: it constrains aggregate resource consumption and object counts within a namespace. That is useful for shared AI platform governance, but namespace quota alone does not express queue admission, accelerator flavor placement, or cohort borrowing. [source note](../../raw/links/kubernetes-kueue-quota-governance-official-20260707.md)

Kueue fills the batch and accelerator admission layer. ClusterQueues govern resource pools and admission, ResourceFlavors distinguish node or accelerator classes, and cohorts enable configured quota sharing across ClusterQueues. The existing local Kueue issue corpus remains useful operational evidence, especially because it contains quota, ClusterQueue, ResourceFlavor, and cohort issues, but its comment join is incomplete and should not be treated as complete design documentation. [source note](../../raw/links/kubernetes-kueue-quota-governance-official-20260707.md), [Kueue](../projects/kueue.md)

# RAG Access Policy And Evaluation Data Governance

RAG access policy now has direct infrastructure evidence through Azure AI Search. The documentation covers document-level access control for RAG and agentic systems, permission metadata stored with indexed documents, query-time security trimming against caller claims, and projection of permission fields or sensitivity labels into chunked indexes. This supports retrieval-time authorization and chunk-level permission propagation claims, but it does not prove instant synchronization after source permission changes or correctness across every RAG cache. [source note](../../raw/links/rag-access-policy-pii-governance-official-sources-20260707.md)

PII controls now have a bounded indexing-pipeline source. Azure AI Search PII Detection skill can extract and mask personally identifiable information during enrichment, and Azure Language PII APIs return entity metadata plus redacted outputs. Use this as evidence for a redaction stage in a RAG indexing pipeline; do not treat it as legal-compliance completion or as proof that pre-existing indexes were scrubbed after policy changes. [source note](../../raw/links/rag-access-policy-pii-governance-official-sources-20260707.md)

Catalog and vector-store policy are adjacent governance planes. DataHub policies define actors, privileges, resource targets, tags, domains, containers, glossary terms, and owner-based targeting for metadata access. Weaviate RBAC scopes data-object permissions by collection and tenant filters, while Weaviate multi-tenancy isolates each tenant on a dedicated shard and deletes the shard when the tenant is deleted. These sources support metadata and vector-store access boundaries, not whole-platform incident readiness. [source note](../../raw/links/rag-access-policy-pii-governance-official-sources-20260707.md)

Evaluation data governance now has a dataset-versioning boundary through Langfuse. Dataset items can include inputs, expected outputs, metadata, and source trace links; dataset versions capture item add/update/delete/archive operations so experiments can be tied to a fixed version. This is useful when evaluation examples derive from production RAG traces and must be versioned or retired after data changes. It does not replace retention policy, privacy review, or access audit evidence. [source note](../../raw/links/rag-access-policy-pii-governance-official-sources-20260707.md)

# Cost Attribution And Capacity Planning

NCCL 2.22 cost-estimation evidence is a model/runtime signal, not a platform chargeback system. `ncclGroupSimulateEnd` estimates grouped NCCL operation time for overlap and workload-balancing research, while lazy connection establishment reduces GPU memory overhead and initialization cost. Use it for communication cost-model and capacity-efficiency claims only. [raw](../../raw/crawler/nccl-technical-blog/20260626T015704298674Z-developer-nvidia-com-blog-memory-efficiency-faster-initialization-and-cost-estimation-with-32a1d0c118.md)

OpenCost provides the workload accounting side. Its allocation API supports Kubernetes cost queries over time windows and aggregation dimensions such as workload, namespace, pod, and labels. In AI platforms, OpenCost is most useful when namespaces, job owners, GPU node labels, and queue labels are maintained consistently enough to map accelerator spend back to teams or jobs. [source note](../../raw/links/opencost-cost-attribution-official-20260707.md)

AWS EC2 Capacity Blocks for ML and AWS Service Quotas provide cloud capacity and quota-planning evidence. Capacity Blocks reserve accelerator capacity for selected future windows, while Service Quotas manages account-level quota visibility and quota-increase workflows. These sources support capacity planning and quota governance, but they do not replace in-cluster ResourceQuota, Kueue admission, or OpenCost attribution. [source note](../../raw/links/aws-accelerator-capacity-quota-planning-official-20260707.md)

# Cross-Cloud Chargeback

The cross-cloud chargeback source note fills the cloud-billing side that OpenCost and AWS capacity planning did not fully cover. AWS split cost allocation data exposes Kubernetes workload cost dimensions such as cluster, namespace, pod, workload, and labels, while AWS cost allocation tags provide the resource-tag reporting boundary. Azure cost allocation can redistribute costs by subscription, resource group, or tags, and AKS cost analysis exposes Kubernetes views such as cluster, namespace, asset, and service. Google Cloud adds GKE cost allocation by Kubernetes concepts such as namespaces and labels, with detailed Billing export to BigQuery as the reporting substrate. [source note](../../raw/links/cross-cloud-chargeback-policy-enforcement-official-sources-20260707.md)

For AI platforms, the useful synthesis is a common mapping rather than a single product feature: cloud billing rows and allocation rules have to be joined to Kubernetes namespace/workload labels, queue or job metadata, accelerator node labels, reservations or capacity commitments, and team ownership. This page can now support mechanism-level cross-cloud chargeback discussions, but it should not claim parity. Azure allocation rules exclude purchases such as reservations and savings plans, AWS Capacity Blocks are reservation-window evidence rather than workload accounting, and Google billing export still needs local labels and ownership conventions before accelerator spend becomes auditable chargeback. [source note](../../raw/links/cross-cloud-chargeback-policy-enforcement-official-sources-20260707.md), [source note](../../raw/links/aws-accelerator-capacity-quota-planning-official-20260707.md), [source note](../../raw/links/opencost-cost-attribution-official-20260707.md)

# Policy Enforcement And Audit

Kubernetes admission and audit sources add a bounded policy-enforcement layer. ValidatingAdmissionPolicy uses CEL-based admission validation and bindings with deny, warn, or audit-style actions. Kubernetes audit logging records API-server request activity according to an audit policy. Gatekeeper audit periodically evaluates existing resources against constraints, while Kyverno validate rules and PolicyReports provide policy checking plus resource-level reporting surfaces. These sources support policy-as-code mechanics for AI platform namespaces, accelerator labels, queue configuration, storage/index cleanup jobs, and operator-managed resources. [source note](../../raw/links/policy-enforcement-deletion-retention-audit-official-sources-20260707.md)

This is still not end-to-end RAG enforcement evidence. The existing RAG governance sources separately cover Azure AI Search permission metadata and security trimming, chunk-level permission projection, PII masking, DataHub policy, Weaviate RBAC/tenancy, vector-store delete/TTL controls, source deletion detection, and Langfuse dataset versioning. Policy-as-code and audit logs can make the Kubernetes resource layer inspectable, but a complete enforcement run would still need evidence that source permissions, source deletes or retention events, search/vector indexes, RAG caches, evaluation datasets, timing, and verification all observed the same policy decision. [source note](../../raw/links/rag-access-policy-pii-governance-official-sources-20260707.md), [source note](../../raw/links/source-to-vector-deletion-retention-official-sources-20260707.md), [source note](../../raw/links/policy-enforcement-deletion-retention-audit-official-sources-20260707.md)

# Coverage Boundaries

Use this page as source-backed coverage for `security-governance-cost`:

- fabric-level tenant isolation through NVIDIA Quantum InfiniBand security profiles;
- accelerator partitioning and virtualization through MIG and vGPU;
- confidential-computing attestation as a trust boundary;
- namespace quota through Kubernetes ResourceQuota;
- queued workload admission through Kueue ClusterQueue, ResourceFlavor, and cohort concepts;
- RAG document-level access metadata, query-time security trimming, chunk permission projection, and PII masking hooks;
- metadata access policy through DataHub policies;
- vector-store RBAC and tenant-scoped object isolation through Weaviate;
- evaluation dataset versioning through Langfuse;
- Kubernetes workload cost allocation through OpenCost;
- AWS, Azure, and Google Cloud cost allocation dimensions that can be normalized through tags, labels, namespaces, workloads, and ownership metadata;
- cloud accelerator capacity reservation and account quota planning through AWS EC2 Capacity Blocks and Service Quotas;
- Kubernetes admission policy, audit logging, Gatekeeper audit, Kyverno validation, and policy reports as policy-as-code enforcement and audit-reporting mechanics;
- NCCL runtime cost-estimation and resource-efficiency evidence only where the claim is about communication or communicator initialization.

Do not use this page to claim complete compliance posture, legal governance, end-to-end data/RAG policy enforcement, cross-cloud chargeback parity, or production incident readiness. Those remain future gaps.

# Citations

- [NVIDIA Quantum InfiniBand multi-tenant security raw capture](../../raw/crawler/nccl-nvidia-blog-wide/20260626T015710841547Z-developer-nvidia-com-blog-one-click-multi-tenant-security-with-nvidia-quantum-infiniband-5b2cd4e1d4.md)
- [NVIDIA GPU isolation and confidential-computing source note](../../raw/links/nvidia-gpu-isolation-confidential-computing-official-20260707.md)
- [Kubernetes and Kueue quota governance source note](../../raw/links/kubernetes-kueue-quota-governance-official-20260707.md)
- [OpenCost cost allocation source note](../../raw/links/opencost-cost-attribution-official-20260707.md)
- [AWS accelerator capacity and service quota source note](../../raw/links/aws-accelerator-capacity-quota-planning-official-20260707.md)
- [RAG access policy, PII, and evaluation governance source note](../../raw/links/rag-access-policy-pii-governance-official-sources-20260707.md)
- [Cross-cloud chargeback and cost allocation source note](../../raw/links/cross-cloud-chargeback-policy-enforcement-official-sources-20260707.md)
- [Policy enforcement, deletion-retention, and audit source note](../../raw/links/policy-enforcement-deletion-retention-audit-official-sources-20260707.md)
- [NCCL 2.22 cost-estimation raw capture](../../raw/crawler/nccl-technical-blog/20260626T015704298674Z-developer-nvidia-com-blog-memory-efficiency-faster-initialization-and-cost-estimation-with-32a1d0c118.md)
- [NVIDIA BlueField-3 raw capture](../../raw/crawler/compute-accelerators-nvidia-bluefield-3/20260627T153315013778Z-www-nvidia-com-en-us-networking-products-data-processing-unit-d517920f8d.md)
- [Kueue closed issues summary](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-summary.json)
