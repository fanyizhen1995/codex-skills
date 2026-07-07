---
type: RawSource
title: AWS Accelerator Capacity And Service Quota Planning Documentation
source_kind: web
url: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-capacity-blocks.html
related_urls:
  - https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html
captured: 2026-07-07
status: ingested
---
# Source

Official AWS documentation:

- Amazon EC2 Capacity Blocks for ML: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-capacity-blocks.html
- AWS Service Quotas User Guide: https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html

Captured as a concise source note for `ai_infra` accelerator capacity-planning and quota-governance coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- EC2 Capacity Blocks for ML are an AWS capacity-reservation mechanism for machine-learning workloads that need accelerator instances for a selected future time window.
- Capacity Blocks are capacity-planning evidence: they address whether accelerator capacity is reserved for a time window, not how a Kubernetes platform attributes cost after a job runs.
- AWS Service Quotas is the AWS service for viewing and managing account-level quota limits and requesting quota increases.
- Service quotas are cloud-account governance evidence; they complement platform-level ResourceQuota or Kueue controls but do not replace in-cluster admission policy.
- For AI infrastructure, capacity blocks and service quotas should be linked to accelerator placement, reservation windows, and team/job attribution labels before being used for platform capacity planning.

# Use In Wiki

Use this source note for source-backed claims about accelerator capacity reservation, service-quota management, and the boundary between cloud capacity planning and in-cluster quota/cost attribution.
