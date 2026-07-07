---
type: RawSource
title: Cross-Cloud Chargeback And Cost Allocation Official Sources
source_kind: web
url: https://docs.aws.amazon.com/cur/latest/userguide/split-cost-allocation-data.html
secondary_urls:
  - https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/custom-tags.html
  - https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/allocate-costs
  - https://learn.microsoft.com/en-us/azure/aks/cost-analysis
  - https://docs.cloud.google.com/kubernetes-engine/docs/how-to/cost-allocations
  - https://cloud.google.com/billing/docs/how-to/export-data-bigquery
captured: 2026-07-07
status: ingested
---
# Source

Official AWS Cost and Usage Reports split cost allocation data documentation: https://docs.aws.amazon.com/cur/latest/userguide/split-cost-allocation-data.html

Official AWS user-defined cost allocation tags documentation: https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/custom-tags.html

Official Azure cost allocation documentation: https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/allocate-costs

Official Azure AKS cost analysis documentation: https://learn.microsoft.com/en-us/azure/aks/cost-analysis

Official Google Kubernetes Engine cost allocation documentation: https://docs.cloud.google.com/kubernetes-engine/docs/how-to/cost-allocations

Official Google Cloud Billing export to BigQuery documentation: https://cloud.google.com/billing/docs/how-to/export-data-bigquery

Captured as a concise source note for `ai_infra` cross-cloud cost attribution and chargeback evidence. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- AWS split cost allocation data can split shared containerized environment costs across Kubernetes workloads, and the split data includes Kubernetes allocation dimensions such as cluster, namespace, pod, workload, and labels.
- AWS user-defined cost allocation tags are account/resource tag keys that can be activated for cost allocation reporting after resources are tagged; this is the AWS resource-tag boundary for chargeback.
- Azure cost allocation rules can redistribute costs among subscriptions, resource groups, or tags, and Azure AKS cost analysis gives Kubernetes views such as cluster, namespace, asset, and service views for AKS cost review.
- Azure cost allocation documentation explicitly excludes purchases, including reservations and savings plans, from allocation rules. Treat Azure reservation reporting as an adjacent commitment-management boundary rather than the same mechanism as AKS namespace cost allocation.
- Google Kubernetes Engine cost allocation can break down cluster costs by Kubernetes concepts such as namespace and label when cost allocation is enabled for a cluster.
- Google Cloud Billing export to BigQuery is the durable reporting boundary for detailed cost and usage analysis; exported rows preserve billing dimensions such as projects and labels that can be joined into chargeback reporting.
- Across AWS, Azure, and Google Cloud, the common chargeback pattern is a join between cloud billing records, resource tags or labels, Kubernetes namespace/workload labels, and team/job ownership metadata.
- This source set does not prove complete cross-cloud chargeback parity. It proves that each cloud exposes cost-allocation dimensions that can be normalized by platform convention; accelerator reservations, account quotas, queue admission, and Kubernetes labels still need explicit local mapping before a chargeback model is production-ready.

# Use In Wiki

Use this source note for bounded claims about cross-cloud cost allocation and chargeback dimensions across AWS, Azure, Google Cloud, and Kubernetes. Pair it with OpenCost, ResourceQuota, Kueue, AWS Capacity Blocks, and AWS Service Quotas evidence when the claim needs workload attribution, admission/quota governance, or accelerator capacity planning. Do not use it to claim complete parity or a validated financial model without a run, billing export, or organizational ownership mapping.
