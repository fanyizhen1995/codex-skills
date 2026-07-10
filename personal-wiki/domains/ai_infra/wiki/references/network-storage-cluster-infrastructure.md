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
  - ../../raw/links/network-storage-topology-benchmark-official-sources-20260707.md
  - ../../raw/links/network-storage-incident-postmortem-sources-20260707.md
  - ../../raw/links/network-storage-exact-benchmark-results-20260707.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704294457Z-developer-nvidia-com-blog-next-generation-ai-factory-telemetry-with-nvidia-spectrum-x-ethe-ee194b9308.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704297319Z-developer-nvidia-com-blog-ai-fabric-resiliency-and-why-network-convergence-matters-2d9246e4ca.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704297605Z-developer-nvidia-com-blog-networking-reliability-and-observability-at-scale-with-nccl-2-24-db6b475ecf.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704298217Z-developer-nvidia-com-blog-advancing-performance-with-nvidia-sharp-in-network-computing-2154529061.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704299278Z-developer-nvidia-com-blog-oci-accelerates-hpc-ai-and-database-using-roce-and-nvidia-connec-904a22fed4.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704299596Z-developer-nvidia-com-blog-turbocharging-ai-workloads-with-nvidia-spectrum-x-networking-pla-752fd3e399.md
  - ../../raw/crawler/compute-accelerators-aws-trn2/20260627T153315637188Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md
  - ../../raw/crawler/compute-accelerators-nvidia-bluefield-3/20260627T153315013778Z-www-nvidia-com-en-us-networking-products-data-processing-unit-d517920f8d.md
  - ../../raw/crawler/compute-accelerators-resnics-stargate-n1025/20260628T060657022930Z-www-resnics-com-product-stargate-n1025-dpu-8584bb028f.md
  - ../../raw/crawler/compute-accelerators-resnics-stargate-n2025/20260628T060657411423Z-www-resnics-com-product-stargate-n2025-dpu-f2feeec038.md
  - ../../raw/crawler/compute-accelerators-resnics-stargate-s1100/20260628T060657808728Z-www-resnics-com-product-stargate-s1100-nvme-of-e3a4fe3da7.md
  - ../../raw/crawler/compute-accelerators-corigine-agilio-cx-pdf/20260628T060444859456Z-storage-corigine-com-cn-uploadfiles-pdf-2022-01-24-1-agilio-20cx-202x25gbe-20smartnic-20-e-a138a8aa07.md
  - ../../raw/crawler/compute-accelerators-jaguarmicro-yunxiao-dpu/20260628T060651455844Z-www-jaguarmicro-com-n4-html-87a5670154.md
  - ../../raw/crawler/compute-accelerators-yusur-k2-pro/20260628T060700357328Z-www-yusur-tech-dpu-k2-pro-c4119da6b0.md
  - ../../raw/crawler/compute-accelerators-yusur-swift-2200n/20260628T060700719790Z-www-yusur-tech-product-swift-swift2200n-7afeac0475.md
  - ../../raw/crawler/compute-accelerators-asterfusion-helium-dpu/20260706T204116820726Z-asterfusion-com-product-helium-dpu-121181ec67.md
  - ../../raw/crawler/compute-accelerators-asterfusion-cx102s-dpu/20260706T204116541565Z-asterfusion-com-product-cx102s-dpu-b77dd4635a.md
  - ../../manifest-ai-infra-expansion-2026-07-07-r10-task-3-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-1-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-3-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-7-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-9-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-15-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-18-gap-proof.json
  - ../../raw/crawler/nccl-aws-hpc-blog/20260705T041042318130Z-aws-amazon-com-blogs-hpc-the-complete-picture-unified-monitoring-for-aws-parallel-computin-ba8cb4538e.md
  - ../../raw/crawler/nccl-lambda-blog/20260705T041046327361Z-lambda-ai-blog-unbox-one-of-nvidias-first-co-packaged-optics-samples-with-lambda-4588e36fba.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260708T233633797183Z-github-com-sgl-project-sglang-pull-30254-0a75111a32.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260708T233633803455Z-github-com-sgl-project-sglang-pull-29716-b6242f612e.md
updated: 2026-07-10
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

The layer remains partial. The evidence now covers EFA, FSx for Lustre, WEKA, Ceph, and SPDK/NVMe-oF at an architecture and source-note level; AWS HyperPod topology-aware scheduling, EFA health checks, node replacement, and checkpoint-aware resume as managed training-cluster data-path evidence; and MLCommons Storage as benchmark-method and result-framework evidence. R9 task 3 adds blocked-source evidence for exact MLCommons measured-result artifacts: local search found no captured per-submission result file, and bounded GitHub API/raw probes failed with local DNS resolution errors. Existing local evidence still covers Spectrum-X/RoCE, BGP PIC convergence, ECN/DC-QCN, SHARP, NIC Fusion, fabric telemetry, and product-specific DPU/NVMe-oF signals. Remaining gaps include complete production incident/postmortem sources, product-specific benchmark submissions with full environment and measured results, and broader non-AWS/non-NVIDIA fabric operations.

# Duplicate Boundaries

Use [NCCL Technical Blog Network Observability](nccl-technical-blog-network-observability.md) for NCCL-adjacent communication, Spectrum-X/RoCE telemetry, convergence, RAS, SHARP, and NIC Fusion. This page reuses that evidence only to keep the fabric layer connected; it does not repeat the full NCCL observability synthesis. [wiki](nccl-technical-blog-network-observability.md)

Use [Compute Accelerator Parameter Comparison](compute-accelerator-parameter-comparison.md) for DPU, SmartNIC, and NVMe-oF product rows. This page uses those rows as local product signals, but does not promote a card specification into a broad storage architecture claim unless a storage-fabric source supports the behavior. [wiki](compute-accelerator-parameter-comparison.md)

Use [Security Governance Cost Infrastructure](security-governance-cost-infrastructure.md) for tenant isolation, quota governance, cost attribution, and cloud capacity planning. EFA, FSx for Lustre, WEKA, Ceph, and NVMe-oF evidence here is about data movement and storage paths, not governance or chargeback. [wiki](security-governance-cost-infrastructure.md)

# Cluster Fabric

AWS Elastic Fabric Adapter is non-NVIDIA fabric evidence for EC2-based AI/HPC clusters. The official EFA docs describe an EC2 network interface for high-performance computing and machine-learning workloads, with an OS-bypass communication path and libfabric integration. Treat EFA as an application/runtime integration boundary, not just as a throughput value on an instance table. [source note](../../raw/links/aws-efa-ai-cluster-networking-official-20260707.md)

The local AWS Trainium2 capture is adjacent EFA evidence because it records EFAv3 interconnect values for Trn2 and Trn2 UltraServer cloud offerings. Use that raw capture for the cloud-offering record, and the EFA source note for the fabric behavior. [raw](../../raw/crawler/compute-accelerators-aws-trn2/20260627T153315637188Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md) [source note](../../raw/links/aws-efa-ai-cluster-networking-official-20260707.md)

Existing local NVIDIA technical-blog evidence remains the strongest fabric operations corpus. It covers Spectrum-X telemetry, BGP Prefix Independent Convergence, RoCE congestion behavior, ECN/DC-QCN design, NIC Fusion, SHARP in-network collective offload, and NCCL RAS. That evidence is valid for NVIDIA/Spectrum-X/RoCE cluster fabric claims, but it does not close EFA, Lustre, WEKA, Ceph, or generic storage gaps. [wiki](nccl-technical-blog-network-observability.md)

The local BlueField platform capture adds a bounded AI-factory DPU platform
signal: BlueField-4 DPU is described as an 800Gb/s infrastructure platform for
gigascale AI factories, and the same page positions BlueField with Spectrum-X
and CMX context-memory storage for long-context, multi-turn, and agentic
inference. Use this as product-boundary evidence for DPU-assisted AI networking
and context-tier adjacency. It is not proof of a storage benchmark,
production-operation loop, service SLO, storage throughput, fabric topology, or
complete CMX deployment. [raw](../../raw/crawler/compute-accelerators-nvidia-bluefield-3/20260627T153315013778Z-www-nvidia-com-en-us-networking-products-data-processing-unit-d517920f8d.md)

The AWS Parallel Computing Service monitoring capture adds an operations-dashboard view of cluster fabric and storage surfaces. Its Managed Grafana dashboards include Jobs, Nodes, GPUs, Slurm, Amazon FSx for Lustre, Logs, Partitions, and EFA, and the architecture sends Slurm, EFA, Node, and DCGM exporter metrics to Amazon Managed Service for Prometheus while pulling instance details from CloudWatch Logs. This is dashboard and observability coverage for cluster operators, not evidence of a production incident response loop, fabric SLO, or product/provider benchmark result. [raw](../../raw/crawler/nccl-aws-hpc-blog/20260705T041042318130Z-aws-amazon-com-blogs-hpc-the-complete-picture-unified-monitoring-for-aws-parallel-computin-ba8cb4538e.md)

# Shared And Parallel Storage

Amazon FSx for Lustre is managed Lustre evidence for shared high-performance filesystems. The AWS documentation positions FSx for Lustre for compute-intensive workloads including machine learning and HPC, and the source note records the S3-linked data repository boundary that matters for dataset staging. Use it for shared training data, scratch, and checkpoint filesystem claims; do not infer EFA or NVMe-oF behavior from it. [source note](../../raw/links/aws-fsx-lustre-parallel-filesystem-official-20260707.md)

WEKA evidence adds a distributed filesystem/storage architecture boundary. The official documentation source note captures filesystem constructs, client mount boundaries, storage-network separation, and GPU-direct storage adjacency where the cited WEKA docs support it. Use WEKA as storage platform evidence, not as a generic proof of model-runtime scheduling or accelerator isolation. [source note](../../raw/links/weka-ai-storage-architecture-official-20260707.md)

Ceph evidence covers distributed storage primitives rather than AI-specific behavior. The official Ceph docs source note separates RADOS storage-cluster architecture, CephFS file interface, and RBD block-device semantics. Use Ceph when the claim is about distributed file or block storage building blocks; pair it with another source before claiming AI training or checkpoint behavior. [source note](../../raw/links/ceph-distributed-storage-official-docs-20260707.md)

# Storage Fabrics And Offload

SPDK NVMe-oF documentation supplies protocol-level storage-fabric evidence. The source note records that SPDK exposes NVMe subsystems and namespaces through an NVMe over Fabrics target, which is broader than any one storage accelerator SKU. Use it to explain the storage path and target/subsystem/namespace boundary; do not use it for AI workload performance claims without a benchmark or deployment source. [source note](../../raw/links/spdk-nvme-of-target-official-docs-20260707.md)

The July 8 SGLang page supplement adds two runtime-adjacent storage signals. PR #30254 is closed without a merged timestamp and describes a PD-disaggregation Mooncake RDMA KV data-race boundary: CUDA compute-stream writes to a KV chunk are not ordered with an RDMA NIC reading GPU memory through PCIe DMA, so the NIC can transmit stale or partially written data if the transfer is issued before kernels complete. The proposed mitigation records a CUDA event on enqueue and synchronizes in the transfer worker before `batch_transfer_sync_write`, but this page should be treated as closed-unmerged evidence rather than a shipped fix. PR #29716 is a merged HiCacheFile storage signal: optional client-side metadata caching avoids repeated filesystem metadata scans when many cache files sit on a shared filesystem, with TTL, startup scan, write backfill, cache-hit bypass, and eviction invalidation boundaries. Its Lustre benchmark table is source context only, not a general storage benchmark, SLO, product ranking, or local result. [Mooncake RDMA raw](../../raw/crawler/sglang-github-closed-issues-prs/20260708T233633797183Z-github-com-sgl-project-sglang-pull-30254-0a75111a32.md) [HiCacheFile raw](../../raw/crawler/sglang-github-closed-issues-prs/20260708T233633803455Z-github-com-sgl-project-sglang-pull-29716-b6242f612e.md)

Local DPU and storage-accelerator captures remain useful product signals. R10
task 3 moves a bounded Resnics subset into the structured catalog:
Stargate-N1025 for DPU SmartNIC form factor, data-port bandwidth, memory, host
interface, and power; and Stargate-S1100 for NVMe-oF host interface, power,
4K/4-SSD read/write IOPS, and added-latency upper bounds. The 2026-07-08
continuation adds Corigine Agilio CX 2x25GbE as a structured SmartNIC product
row for port bandwidth, onboard memory, and PCIe host interface from its
official product brief. Continuation parent 3 adds Yusur K2-Pro
product-specific catalog rows for DPU form factor, 200 Gb/s source-stated
network bandwidth, and `2 x PCIe Gen3 x16`, plus a SWIFT-2200N Pro DPU-card
form-factor row. Continuation parent 7 adds Resnics Stargate-N2025
product-specific DPU SmartNIC catalog rows for form factor, aggregate 50 Gb/s
data-port bandwidth, split-pool DDR4 memory capacity, `PCIe Gen4 x8`, and
150 W power. Continuation parent 9 adds Asterfusion Helium and CX102S as
product-specific DPU catalog signals: Helium resolves PCIe DPU SmartNIC form
factor, 100 Gb/s source-stated mixed-service processing capability, expandable
64 GB memory, `PCIe x8 Gen3.0/4.0`, and 60 W source comparison power, while
CX102S resolves a DPU module inside a 1U gateway with 8 GB DDR4 module memory.
Continuation parent 15 adds JaguarMicro Yunxiao DPU as a structured product
signal for aggregate 50 Gb/s Ethernet bandwidth from its 2 x 25G announcement
text.
Continuation parent 18 adds NVIDIA BlueField-4 DPU as a structured product
signal for only 800 Gb/s network bandwidth. The same platform page mentions
BlueField-4 STX, CMX context-memory storage, accelerated storage for AI,
NVMe-oF, GPUDirect Storage, block/file/object support, rapid data access, and
high-performance inference, but those are retained here as boundary context and
not generalized into catalog storage fields, protocol-level storage-fabric
behavior, benchmark results, operations evidence, or SLO claims.

N2025 SR-IOV, RDMA, P4/session/protocol, storage-offload, line-rate,
low-latency, benchmark, and production-operation text remains product-page
boundary evidence rather than protocol-level storage-fabric, benchmark,
operations, or SLO evidence. CX102S 72 Gb/s switching capacity, gateway port
layout, and Helium NFV/session/offload/storage-acceleration text likewise
remain product-page boundary evidence rather than protocol-level storage-fabric,
benchmark, operations, or SLO claims. K2-Pro NVMe-oF engine and unspecified
2M IOPS, plus SWIFT PCIe pass-through latency, loopback latency, and jitter,
remain comparison-only product evidence rather than protocol-level
storage-fabric, benchmark, or SLO claims. JaguarMicro RoCE v1/v2, iWARP,
NVMe-oF, VLAN, VXLAN, GRE, Geneve, L2VPN, virtio acceleration, elastic
storage/network, security, QoS, hot migration, and hot upgrade text remains
product-page boundary evidence rather than resolved protocol, storage-fabric,
benchmark, operations, or SLO claims. Keep product claims tied to catalog rows,
and use SPDK or another storage-fabric source for protocol-level behavior.
[wiki](compute-accelerator-parameter-comparison.md)
[raw](../../raw/crawler/compute-accelerators-resnics-stargate-n1025/20260628T060657022930Z-www-resnics-com-product-stargate-n1025-dpu-8584bb028f.md)
[raw](../../raw/crawler/compute-accelerators-resnics-stargate-n2025/20260628T060657411423Z-www-resnics-com-product-stargate-n2025-dpu-f2feeec038.md)
[raw](../../raw/crawler/compute-accelerators-resnics-stargate-s1100/20260628T060657808728Z-www-resnics-com-product-stargate-s1100-nvme-of-e3a4fe3da7.md)
[raw](../../raw/crawler/compute-accelerators-corigine-agilio-cx-pdf/20260628T060444859456Z-storage-corigine-com-cn-uploadfiles-pdf-2022-01-24-1-agilio-20cx-202x25gbe-20smartnic-20-e-a138a8aa07.md)
[raw](../../raw/crawler/compute-accelerators-jaguarmicro-yunxiao-dpu/20260628T060651455844Z-www-jaguarmicro-com-n4-html-87a5670154.md)
[raw](../../raw/crawler/compute-accelerators-yusur-k2-pro/20260628T060700357328Z-www-yusur-tech-dpu-k2-pro-c4119da6b0.md)
[raw](../../raw/crawler/compute-accelerators-yusur-swift-2200n/20260628T060700719790Z-www-yusur-tech-product-swift-swift2200n-7afeac0475.md)
[Helium raw](../../raw/crawler/compute-accelerators-asterfusion-helium-dpu/20260706T204116820726Z-asterfusion-com-product-helium-dpu-121181ec67.md)
[CX102S raw](../../raw/crawler/compute-accelerators-asterfusion-cx102s-dpu/20260706T204116541565Z-asterfusion-com-product-cx102s-dpu-b77dd4635a.md)

# Training Topology And Checkpoint Data Paths

AWS HyperPod adds a concrete managed-training topology boundary beyond the earlier EFA architecture note. HyperPod topology-aware scheduling labels resources by instance and network topology, uses Slurm topology plugins for hierarchical or block placement, and reconciles topology after scale-up, scale-down, and node replacement. Use this as topology-control evidence for AI training clusters; do not infer a workload speedup unless a benchmark source is also cited. [source note](../../raw/links/network-storage-topology-benchmark-official-sources-20260707.md)

HyperPod Slurm cluster documentation also records EFA and FSx for Lustre as cluster configuration surfaces, while the resiliency documentation ties replacement and resume workflows to checkpoint-aware jobs and EFA health checks. That makes checkpoint location, shared filesystem choice, and fabric health part of the training data path rather than separate inventory facts. This is managed-service operations evidence, not a public incident postmortem. [source note](../../raw/links/network-storage-topology-benchmark-official-sources-20260707.md) [source note](../../raw/links/network-storage-incident-postmortem-sources-20260707.md)

# Storage Benchmark Mechanics

MLCommons Storage is the benchmark-method boundary for AI storage in this page. The source note records that MLCommons Storage targets AI training storage behavior, includes workloads such as UNet3D, ResNet50, CosmoFlow, and checkpointing, and publishes result metadata such as storage system, workload, backend, compute-node count, accelerator count, networking, and throughput. Use it to identify whether a future benchmark source has the necessary method and result fields. [source note](../../raw/links/network-storage-topology-benchmark-official-sources-20260707.md)

This page does not rank FSx for Lustre, WEKA, Ceph, SPDK, or NVMe-oF systems from MLCommons results. A future product-specific benchmark claim must cite the exact submission or report and preserve workload, topology, hardware or cloud environment, storage/fabric configuration, and measured result boundaries. [source note](../../raw/links/network-storage-topology-benchmark-official-sources-20260707.md)

# Co-Packaged Optics Planning Boundary

The Lambda/NVIDIA co-packaged optics capture is fabric-planning evidence for large NVIDIA cluster deployments, centered on the Quantum-X Photonics Q3450-LD switch and GB300 NVL72-scale 800G fabrics. Source-visible planning signals include a 4U liquid-cooled switch with 144 x 800G InfiniBand ports and 115.2 Tb/s non-blocking switching capacity, 48V busbar power input, UDQ4 liquid-cooling quick disconnects, removable light-source modules, and front-panel fiber-array connections replacing traditional OSFP transceiver cages. The source frames switch-layer power as a planning constraint, including a 3.95 kW CPO switch versus 7.0 kW standard-switch comparison and roughly 655,000 pluggable transceiver modules as a large-fabric failure-point class. [raw](../../raw/crawler/nccl-lambda-blog/20260705T041046327361Z-lambda-ai-blog-unbox-one-of-nvidias-first-co-packaged-optics-samples-with-lambda-4588e36fba.md)

Use this as early operational-planning evidence: rack fit, busbar alignment, liquid cooling, pressure checks, fiber routing, fiber termination, and installation procedure testing with the vendor. Do not promote it as a production postmortem, generalized availability claim, exact reliability measurement, guaranteed GB300 NVL72 deployment capacity, or accelerator SKU catalog row. [raw](../../raw/crawler/nccl-lambda-blog/20260705T041046327361Z-lambda-ai-blog-unbox-one-of-nvidias-first-co-packaged-optics-samples-with-lambda-4588e36fba.md)

# Exact Result Artifact Probe Boundary

R9 task 3 searched local raw, crawler, GitHub, curated wiki, coverage, and loop-state evidence for exact MLCommons Storage result artifacts and provider benchmark submissions. It found benchmark-method and result-framework evidence, but no local per-submission result file with source-backed submitter, workload, backend, storage system, compute-node count, accelerator count where present, networking/topology, storage configuration, and measured throughput. [source note](../../raw/links/network-storage-exact-benchmark-results-20260707.md)

The same task attempted bounded official GitHub API and raw-result probes for `mlcommons/storage_results_v2.0`, but the shell sandbox returned `Temporary failure in name resolution`. Because exact result-file content was not captured, this page still does not promote throughput, ranking, or product/provider benchmark-performance claims from MLCommons Storage. [source note](../../raw/links/network-storage-exact-benchmark-results-20260707.md)

# Incident And Postmortem Boundary

No new production incident or postmortem source was promoted in this task. The incident search note records probes for EFA, RoCE/Spectrum-X, Lustre, WEKA, Ceph, and NVMe-oF incident/postmortem sources, but the available probes did not produce a primary source with impact, timeline, environment, remediation, and follow-up ownership. Keep HyperPod resiliency and local issue evidence scoped to operational mechanics or incident-shaped leads. [source note](../../raw/links/network-storage-incident-postmortem-sources-20260707.md)

# Coverage Use

Use this page as source-backed coverage for `network-storage-cluster`:

- EFA as EC2 AI/HPC fabric evidence with OS-bypass and libfabric integration boundaries;
- FSx for Lustre as managed Lustre/shared filesystem evidence for compute-intensive ML/HPC workloads and S3-linked dataset staging;
- WEKA as distributed filesystem/storage architecture evidence, including client mount and storage-network boundaries;
- Ceph as distributed storage evidence for RADOS, CephFS, and RBD file/block primitives;
- SPDK NVMe-oF as storage-fabric protocol evidence for target/subsystem/namespace behavior;
- AWS HyperPod topology-aware scheduling, Slurm topology plugin behavior, EFA health checks, node replacement, and checkpoint-aware resume as managed training-cluster topology and data-path evidence;
- AWS PCS dashboard coverage for Slurm/EFA/Node/DCGM exporter metrics, CloudWatch Logs, and Jobs/Nodes/GPUs/Slurm/FSx/EFA/Logs views;
- Lambda/NVIDIA CPO planning evidence for Quantum-X Photonics Q3450-LD, 800G/GB300 NVL72 fabric power, reliability, cooling, fiber routing, and installation-procedure boundaries;
- MLCommons Storage benchmark mechanics and result-framework fields for AI storage benchmarking;
- SGLang page-level Mooncake RDMA KV-transfer ordering evidence and HiCacheFile filesystem metadata-cache behavior, while preserving closed-unmerged and benchmark-context caveats;
- blocked-source evidence showing exact MLCommons measured-result artifacts were not available from local corpus or bounded shell probes in r9 task 3;
- existing NCCL technical-blog evidence for Spectrum-X/RoCE fabric telemetry, convergence, congestion control, SHARP, NIC Fusion, and RAS;
- local DPU/SmartNIC/NVMe-oF product captures only for product-specific storage or offload signals.
- NVIDIA BlueField-4 DPU and CMX/STX context only as product-boundary evidence for AI-factory networking/storage/security adjacency, not as benchmark or production-operation proof.

Do not use this page to claim complete production incident readiness, product-specific benchmark leadership, or full non-NVIDIA fabric operations. Those remain future gaps.

# Citations

- [AWS EFA source note](../../raw/links/aws-efa-ai-cluster-networking-official-20260707.md)
- [AWS FSx for Lustre source note](../../raw/links/aws-fsx-lustre-parallel-filesystem-official-20260707.md)
- [WEKA storage architecture source note](../../raw/links/weka-ai-storage-architecture-official-20260707.md)
- [Ceph distributed storage source note](../../raw/links/ceph-distributed-storage-official-docs-20260707.md)
- [SPDK NVMe-oF source note](../../raw/links/spdk-nvme-of-target-official-docs-20260707.md)
- [Network storage topology and benchmark source note](../../raw/links/network-storage-topology-benchmark-official-sources-20260707.md)
- [Network storage incident and postmortem source search](../../raw/links/network-storage-incident-postmortem-sources-20260707.md)
- [Network storage exact benchmark result source probe](../../raw/links/network-storage-exact-benchmark-results-20260707.md)
- [NCCL Technical Blog Network Observability](nccl-technical-blog-network-observability.md)
- [Compute Accelerator Parameter Comparison](compute-accelerator-parameter-comparison.md)
- [AWS Trainium2 raw capture](../../raw/crawler/compute-accelerators-aws-trn2/20260627T153315637188Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md)
- [NVIDIA BlueField platform raw capture](../../raw/crawler/compute-accelerators-nvidia-bluefield-3/20260627T153315013778Z-www-nvidia-com-en-us-networking-products-data-processing-unit-d517920f8d.md)
- [Continuation parent-18 NVIDIA BlueField-4 gap proof](../../manifest-ai-infra-expansion-continuation-20260708-parent-18-gap-proof.json)
- [Resnics Stargate-N2025 raw capture](../../raw/crawler/compute-accelerators-resnics-stargate-n2025/20260628T060657411423Z-www-resnics-com-product-stargate-n2025-dpu-f2feeec038.md)
- [Resnics Stargate-S1100 raw capture](../../raw/crawler/compute-accelerators-resnics-stargate-s1100/20260628T060657808728Z-www-resnics-com-product-stargate-s1100-nvme-of-e3a4fe3da7.md)
- [Corigine Agilio CX raw capture](../../raw/crawler/compute-accelerators-corigine-agilio-cx-pdf/20260628T060444859456Z-storage-corigine-com-cn-uploadfiles-pdf-2022-01-24-1-agilio-20cx-202x25gbe-20smartnic-20-e-a138a8aa07.md)
- [JaguarMicro Yunxiao DPU raw capture](../../raw/crawler/compute-accelerators-jaguarmicro-yunxiao-dpu/20260628T060651455844Z-www-jaguarmicro-com-n4-html-87a5670154.md)
- [Continuation parent-15 JaguarMicro Yunxiao DPU gap proof](../../manifest-ai-infra-expansion-continuation-20260708-parent-15-gap-proof.json)
- [Yusur K2-Pro raw capture](../../raw/crawler/compute-accelerators-yusur-k2-pro/20260628T060700357328Z-www-yusur-tech-dpu-k2-pro-c4119da6b0.md)
- [Yusur SWIFT-2200N Pro raw capture](../../raw/crawler/compute-accelerators-yusur-swift-2200n/20260628T060700719790Z-www-yusur-tech-product-swift-swift2200n-7afeac0475.md)
- [Continuation parent-3 Yusur gap proof](../../manifest-ai-infra-expansion-continuation-20260708-parent-3-gap-proof.json)
- [Continuation parent-7 Resnics N2025 gap proof](../../manifest-ai-infra-expansion-continuation-20260708-parent-7-gap-proof.json)
- [Asterfusion Helium raw capture](../../raw/crawler/compute-accelerators-asterfusion-helium-dpu/20260706T204116820726Z-asterfusion-com-product-helium-dpu-121181ec67.md)
- [Asterfusion CX102S-DPU raw capture](../../raw/crawler/compute-accelerators-asterfusion-cx102s-dpu/20260706T204116541565Z-asterfusion-com-product-cx102s-dpu-b77dd4635a.md)
- [Continuation parent-9 Asterfusion gap proof](../../manifest-ai-infra-expansion-continuation-20260708-parent-9-gap-proof.json)
- [AWS Parallel Computing Service monitoring capture](../../raw/crawler/nccl-aws-hpc-blog/20260705T041042318130Z-aws-amazon-com-blogs-hpc-the-complete-picture-unified-monitoring-for-aws-parallel-computin-ba8cb4538e.md)
- [Lambda/NVIDIA co-packaged optics capture](../../raw/crawler/nccl-lambda-blog/20260705T041046327361Z-lambda-ai-blog-unbox-one-of-nvidias-first-co-packaged-optics-samples-with-lambda-4588e36fba.md)
- [SGLang PR #30254 Mooncake RDMA KV data race](../../raw/crawler/sglang-github-closed-issues-prs/20260708T233633797183Z-github-com-sgl-project-sglang-pull-30254-0a75111a32.md)
- [SGLang PR #29716 HiCacheFile metadata cache](../../raw/crawler/sglang-github-closed-issues-prs/20260708T233633803455Z-github-com-sgl-project-sglang-pull-29716-b6242f612e.md)
