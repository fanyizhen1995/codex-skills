---
type: Reference
title: Network Storage Cluster Infrastructure
description: Source-backed reference for AI cluster networking, parallel/shared storage, distributed storage, and storage-fabric boundaries beyond NCCL and accelerator SKU tables.
domain: ai_infra
status: reviewed
aliases:
  - AI cluster network storage infrastructure
  - network storage cluster infrastructure
  - EFA Lustre Weka Ceph NVMe-oF infrastructure
tags:
  - network-fabric
  - storage
  - cluster-infrastructure
  - efa
  - lustre
  - ceph
  - nvme-of
source_refs:
  - ../../raw/links/aws-efa-ai-cluster-networking-official-20260707.md
  - ../../raw/links/aws-fsx-lustre-parallel-filesystem-official-20260707.md
  - ../../raw/links/weka-ai-storage-architecture-official-20260707.md
  - ../../raw/links/ceph-distributed-storage-official-docs-20260707.md
  - ../../raw/links/spdk-nvme-of-target-official-docs-20260707.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704294457Z-developer-nvidia-com-blog-next-generation-ai-factory-telemetry-with-nvidia-spectrum-x-ethe-ee194b9308.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704297319Z-developer-nvidia-com-blog-ai-fabric-resiliency-and-why-network-convergence-matters-2d9246e4ca.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704297605Z-developer-nvidia-com-blog-networking-reliability-and-observability-at-scale-with-nccl-2-24-db6b475ecf.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704298217Z-developer-nvidia-com-blog-advancing-performance-with-nvidia-sharp-in-network-computing-2154529061.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704299278Z-developer-nvidia-com-blog-oci-accelerates-hpc-ai-and-database-using-roce-and-nvidia-connec-904a22fed4.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704299596Z-developer-nvidia-com-blog-turbocharging-ai-workloads-with-nvidia-spectrum-x-networking-pla-752fd3e399.md
  - ../../raw/crawler/compute-accelerators-aws-trn2/20260627T153315637188Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md
  - ../../raw/crawler/compute-accelerators-resnics-stargate-s1100/20260628T060657808728Z-www-resnics-com-product-stargate-s1100-nvme-of-e3a4fe3da7.md
  - ../../raw/crawler/compute-accelerators-jaguarmicro-yunxiao-dpu/20260628T060651455844Z-www-jaguarmicro-com-n4-html-87a5670154.md
  - ../../raw/crawler/compute-accelerators-yusur-k2-pro/20260628T060700357328Z-www-yusur-tech-dpu-k2-pro-c4119da6b0.md
updated: 2026-07-07
related:
  - ai-infra-coverage-map.md
  - nccl-technical-blog-network-observability.md
  - compute-accelerator-parameter-comparison.md
  - security-governance-cost-infrastructure.md
---
# Summary

This reference fills the `network-storage-cluster` layer beyond existing NCCL/Spectrum-X coverage and accelerator SKU tables. It separates four infrastructure surfaces that are often conflated:

- cluster fabric for GPU/AI communication;
- shared or parallel filesystems for datasets, checkpoints, and scratch data;
- distributed storage building blocks for file and block interfaces;
- storage-fabric or offload paths such as NVMe-oF.

The layer remains partial. The new evidence covers EFA, FSx for Lustre, WEKA, Ceph, and SPDK/NVMe-oF at an architecture and source-note level, while existing local evidence still covers Spectrum-X/RoCE, BGP PIC convergence, ECN/DC-QCN, SHARP, NIC Fusion, fabric telemetry, and product-specific DPU/NVMe-oF signals. Remaining gaps include incident evidence, topology diagrams, workload-specific storage benchmarks, non-NVIDIA fabric operations, and direct training/checkpoint case studies.

# Duplicate Boundaries

Use [NCCL Technical Blog Network Observability](nccl-technical-blog-network-observability.md) for NCCL-adjacent communication, Spectrum-X/RoCE telemetry, convergence, RAS, SHARP, and NIC Fusion. This page reuses that evidence only to keep the fabric layer connected; it does not repeat the full NCCL observability synthesis. [wiki](nccl-technical-blog-network-observability.md)

Use [Compute Accelerator Parameter Comparison](compute-accelerator-parameter-comparison.md) for DPU, SmartNIC, and NVMe-oF product rows. This page uses those rows as local product signals, but does not promote a card specification into a broad storage architecture claim unless a storage-fabric source supports the behavior. [wiki](compute-accelerator-parameter-comparison.md)

Use [Security Governance Cost Infrastructure](security-governance-cost-infrastructure.md) for tenant isolation, quota governance, cost attribution, and cloud capacity planning. EFA, FSx for Lustre, WEKA, Ceph, and NVMe-oF evidence here is about data movement and storage paths, not governance or chargeback. [wiki](security-governance-cost-infrastructure.md)

# Cluster Fabric

AWS Elastic Fabric Adapter is non-NVIDIA fabric evidence for EC2-based AI/HPC clusters. The official EFA docs describe an EC2 network interface for high-performance computing and machine-learning workloads, with an OS-bypass communication path and libfabric integration. Treat EFA as an application/runtime integration boundary, not just as a throughput value on an instance table. [source note](../../raw/links/aws-efa-ai-cluster-networking-official-20260707.md)

The local AWS Trainium2 capture is adjacent EFA evidence because it records EFAv3 interconnect values for Trn2 and Trn2 UltraServer cloud offerings. Use that raw capture for the cloud-offering record, and the EFA source note for the fabric behavior. [raw](../../raw/crawler/compute-accelerators-aws-trn2/20260627T153315637188Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md) [source note](../../raw/links/aws-efa-ai-cluster-networking-official-20260707.md)

Existing local NVIDIA technical-blog evidence remains the strongest fabric operations corpus. It covers Spectrum-X telemetry, BGP Prefix Independent Convergence, RoCE congestion behavior, ECN/DC-QCN design, NIC Fusion, SHARP in-network collective offload, and NCCL RAS. That evidence is valid for NVIDIA/Spectrum-X/RoCE cluster fabric claims, but it does not close EFA, Lustre, WEKA, Ceph, or generic storage gaps. [wiki](nccl-technical-blog-network-observability.md)

# Shared And Parallel Storage

Amazon FSx for Lustre is managed Lustre evidence for shared high-performance filesystems. The AWS documentation positions FSx for Lustre for compute-intensive workloads including machine learning and HPC, and the source note records the S3-linked data repository boundary that matters for dataset staging. Use it for shared training data, scratch, and checkpoint filesystem claims; do not infer EFA or NVMe-oF behavior from it. [source note](../../raw/links/aws-fsx-lustre-parallel-filesystem-official-20260707.md)

WEKA evidence adds a distributed filesystem/storage architecture boundary. The official documentation source note captures filesystem constructs, client mount boundaries, storage-network separation, and GPU-direct storage adjacency where the cited WEKA docs support it. Use WEKA as storage platform evidence, not as a generic proof of model-runtime scheduling or accelerator isolation. [source note](../../raw/links/weka-ai-storage-architecture-official-20260707.md)

Ceph evidence covers distributed storage primitives rather than AI-specific behavior. The official Ceph docs source note separates RADOS storage-cluster architecture, CephFS file interface, and RBD block-device semantics. Use Ceph when the claim is about distributed file or block storage building blocks; pair it with another source before claiming AI training or checkpoint behavior. [source note](../../raw/links/ceph-distributed-storage-official-docs-20260707.md)

# Storage Fabrics And Offload

SPDK NVMe-oF documentation supplies protocol-level storage-fabric evidence. The source note records that SPDK exposes NVMe subsystems and namespaces through an NVMe over Fabrics target, which is broader than any one storage accelerator SKU. Use it to explain the storage path and target/subsystem/namespace boundary; do not use it for AI workload performance claims without a benchmark or deployment source. [source note](../../raw/links/spdk-nvme-of-target-official-docs-20260707.md)

Local DPU and storage-accelerator captures remain useful product signals. Resnics Stargate-S1100 is a local NVMe-oF storage accelerator capture with 100G Ethernet, direct U.2 NVMe SSD attachment, and product-specific IOPS/latency fields. JaguarMicro Yunxiao DPU and Yusur K2-Pro provide local DPU/NVMe-oF engine evidence. Keep those claims tied to product rows, and use SPDK or another storage-fabric source for protocol-level behavior. [raw](../../raw/crawler/compute-accelerators-resnics-stargate-s1100/20260628T060657808728Z-www-resnics-com-product-stargate-s1100-nvme-of-e3a4fe3da7.md) [raw](../../raw/crawler/compute-accelerators-jaguarmicro-yunxiao-dpu/20260628T060651455844Z-www-jaguarmicro-com-n4-html-87a5670154.md) [raw](../../raw/crawler/compute-accelerators-yusur-k2-pro/20260628T060700357328Z-www-yusur-tech-dpu-k2-pro-c4119da6b0.md)

# Coverage Use

Use this page as source-backed coverage for `network-storage-cluster`:

- EFA as EC2 AI/HPC fabric evidence with OS-bypass and libfabric integration boundaries;
- FSx for Lustre as managed Lustre/shared filesystem evidence for compute-intensive ML/HPC workloads and S3-linked dataset staging;
- WEKA as distributed filesystem/storage architecture evidence, including client mount and storage-network boundaries;
- Ceph as distributed storage evidence for RADOS, CephFS, and RBD file/block primitives;
- SPDK NVMe-oF as storage-fabric protocol evidence for target/subsystem/namespace behavior;
- existing NCCL technical-blog evidence for Spectrum-X/RoCE fabric telemetry, convergence, congestion control, SHARP, NIC Fusion, and RAS;
- local DPU/SmartNIC/NVMe-oF product captures only for product-specific storage or offload signals.

Do not use this page to claim complete cluster topology coverage, production incident readiness, full storage-performance benchmarking, or full non-NVIDIA fabric operations. Those remain future gaps.

# Citations

- [AWS EFA source note](../../raw/links/aws-efa-ai-cluster-networking-official-20260707.md)
- [AWS FSx for Lustre source note](../../raw/links/aws-fsx-lustre-parallel-filesystem-official-20260707.md)
- [WEKA storage architecture source note](../../raw/links/weka-ai-storage-architecture-official-20260707.md)
- [Ceph distributed storage source note](../../raw/links/ceph-distributed-storage-official-docs-20260707.md)
- [SPDK NVMe-oF source note](../../raw/links/spdk-nvme-of-target-official-docs-20260707.md)
- [NCCL Technical Blog Network Observability](nccl-technical-blog-network-observability.md)
- [Compute Accelerator Parameter Comparison](compute-accelerator-parameter-comparison.md)
- [AWS Trainium2 raw capture](../../raw/crawler/compute-accelerators-aws-trn2/20260627T153315637188Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md)
- [Resnics Stargate-S1100 raw capture](../../raw/crawler/compute-accelerators-resnics-stargate-s1100/20260628T060657808728Z-www-resnics-com-product-stargate-s1100-nvme-of-e3a4fe3da7.md)
- [JaguarMicro Yunxiao DPU raw capture](../../raw/crawler/compute-accelerators-jaguarmicro-yunxiao-dpu/20260628T060651455844Z-www-jaguarmicro-com-n4-html-87a5670154.md)
- [Yusur K2-Pro raw capture](../../raw/crawler/compute-accelerators-yusur-k2-pro/20260628T060700357328Z-www-yusur-tech-dpu-k2-pro-c4119da6b0.md)
