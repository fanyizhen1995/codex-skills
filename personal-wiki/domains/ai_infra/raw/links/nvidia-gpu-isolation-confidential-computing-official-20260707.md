---
type: RawSource
title: NVIDIA GPU Isolation And Confidential Computing Documentation
source_kind: web
url: https://docs.nvidia.com/datacenter/tesla/mig-user-guide/
related_urls:
  - https://docs.nvidia.com/vgpu/latest/grid-vgpu-user-guide/
  - https://docs.nvidia.com/confidential-computing/
captured: 2026-07-07
status: ingested
---
# Source

Official NVIDIA documentation:

- NVIDIA Multi-Instance GPU User Guide: https://docs.nvidia.com/datacenter/tesla/mig-user-guide/
- NVIDIA vGPU Software User Guide: https://docs.nvidia.com/vgpu/latest/grid-vgpu-user-guide/
- NVIDIA Confidential Computing documentation: https://docs.nvidia.com/confidential-computing/

Captured as a concise source note for `ai_infra` security, tenant-isolation, and accelerator governance coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- The MIG user guide describes Multi-Instance GPU as a way to partition a supported NVIDIA data-center GPU into multiple GPU instances.
- MIG partitions expose isolated GPU instances with dedicated compute and memory resources, which makes MIG a hardware-backed accelerator sharing boundary rather than a scheduler-only policy.
- MIG management is an infrastructure operation: administrators enable MIG mode, create GPU instances, create compute instances, and expose those instances to users or containers.
- NVIDIA vGPU software virtualizes physical GPUs for virtual machines; vGPU profiles define the virtual GPU resource shape presented to a guest.
- vGPU is a hypervisor and profile-governed sharing layer, so it is useful evidence for accelerator allocation policy, virtualized topology, and tenant-facing profile selection.
- NVIDIA confidential computing documentation covers protected GPU workload operation, remote attestation, and trust evidence for confirming the software and hardware state before sensitive workloads run.
- Confidential computing is not a replacement for quota, admission, or network policy. It is evidence for trust and attestation boundaries around sensitive GPU workloads.

# Use In Wiki

Use this source note for source-backed claims about MIG hardware partitioning, vGPU profile-governed virtualization, and NVIDIA confidential-computing attestation as separate AI platform isolation and governance mechanisms.
