---
type: IngestPlan
domain: ai_infra
source_refs:
  - 20260628T060445164573Z-www-dayudpu-com-product-paratus1-70c58cfadc.md
  - ../compute-accelerators-dayu-paratus2/20260628T060445547733Z-www-dayudpu-com-product-paratus2-24678a2fdd.md
task_id: ai-infra-expansion-continuation-20260708-parent-22
status: done
created: 2026-07-10
---

# Dayu Paratus DPU Software Boundary Ingest Plan

## Scope

Promote only source-backed qualitative DPU software-stack and cloud-integration
facts from the existing local Dayu Paratus 1.0 and Paratus 2.0 product-page
captures. No new fetch is needed.

## Duplicate And Gap Check

- Prior parent-1, parent-3, parent-7, parent-9, parent-15, and parent-18
  already cover Corigine, Yusur, Resnics, Asterfusion, JaguarMicro, and
  NVIDIA BlueField DPU/SmartNIC slices.
- R10 task-3 already covers Resnics Stargate-N1025 and Stargate-S1100
  storage-offload catalog fields.
- Dayu Paratus appears only as crawl-inventory and no-parameter comparison
  evidence before this task.

## Curated Updates

- Update `wiki/references/network-storage-cluster-infrastructure.md` with a
  Dayu boundary note: Paratus 1.0 uses Linux on ARM SoC plus DPDK/SPDK
  development kits to move host-side functions onto the DPU and provides
  virtualization-network, storage-client, OpenStack, and Kubernetes integration
  components for bare-metal, VM, and container cloud services.
- Add Paratus 2.0 as the later Dayu DPU product that keeps the same
  software/runtime environment while adding ARM SoC + FPGA architecture,
  FPGA network data-path processing, Dayu HPRT RDMA-adjacent protocol wording,
  end-to-end network data-encryption wording, and upper-layer application
  behavior-analysis wording.
- Update `wiki/references/compute-accelerator-parameter-comparison.md` to keep
  Dayu in the raw comparison layer, with no structured catalog row.
- Update `wiki/references/ai-infra-coverage-map.md`, `coverage-map.json`,
  `loop-state.json`, and `ingest.md` with parent-22 evidence and caveats.

## Non-Promoted Claims

Do not promote network bandwidth, memory capacity, host interface, power, IOPS,
latency, packet rate, throughput, benchmark, production-operation, training or
inference throughput, service-SLO, availability, incident, or protocol-level
storage-fabric claims. The local Dayu captures do not expose schema-supported
numeric fields with explicit product boundaries.
