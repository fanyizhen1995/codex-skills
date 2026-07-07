---
type: RawSource
title: AWS FSx For Lustre Parallel Filesystem Documentation
source_kind: web
url: https://docs.aws.amazon.com/fsx/latest/LustreGuide/what-is.html
captured: 2026-07-07
status: ingested
---
# Source

Official AWS FSx for Lustre documentation: https://docs.aws.amazon.com/fsx/latest/LustreGuide/what-is.html

Captured as a concise source note for `ai_infra` network-storage-cluster and shared training-data storage coverage. The full external page was not mirrored; the durable facts below are paraphrased from the official source.

# Captured Facts

- Amazon FSx for Lustre is a managed file system service based on Lustre, the parallel file system commonly used for workloads that need high-performance shared storage.
- AWS positions FSx for Lustre for compute-intensive workloads, including machine learning, high-performance computing, media processing, and analytics.
- FSx for Lustre is shared filesystem evidence: it addresses how compute fleets access shared files and datasets, not how a model runtime schedules GPU collectives or attributes cloud cost.
- FSx for Lustre can be linked with Amazon S3 data repositories, which makes it relevant to AI training pipelines that stage data between object storage and a high-performance filesystem.
- Use FSx for Lustre as a managed parallel filesystem source. Do not infer Weka, Ceph, NVMe-oF, or local NVMe behavior from this source alone.

# Use In Wiki

Use this source note for source-backed claims about managed Lustre filesystems, shared training data, checkpoint or scratch storage boundaries, and S3-linked dataset staging for AI/HPC clusters.
