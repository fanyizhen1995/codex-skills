---
type: Project
title: Compute Accelerator Spec Catalog
description: Structured catalog for source-backed GPU, NPU, TPU, DPU, IPU, FPGA, DSA, and AI ASIC specifications.
domain: ai_infra
status: reviewed
aliases:
  - accelerator spec catalog
  - compute accelerator catalog
tags:
  - accelerators
  - catalog
  - specs
source_refs:
  - ../../data/compute_accelerators/README.md
  - ../../data/compute_accelerators/skus/sample-skus.yaml
  - ../../data/compute_accelerators/observations/sample-observations.yaml
  - ../../data/compute_accelerators/resolved/sample-resolved-specs.yaml
  - ../../raw/crawler/compute-accelerators-nvidia-h200/20260705T041039962650Z-www-nvidia-com-en-us-data-center-h200-a464325a64.md
  - ../../raw/crawler/compute-accelerators-cambricon-mlu370-x4/20260628T060443305596Z-www-cambricon-com-index-php-56612de611.md
  - ../../raw/crawler/compute-accelerators-cambricon-mlu370-x8/20260628T060443731999Z-www-cambricon-com-index-php-da315093d5.md
  - ../../raw/crawler/compute-accelerators-kunlunxin-rg800/20260628T060652551492Z-www-kunlunxin-com-product-2842-html-6c65e115a3.md
  - ../../raw/crawler/compute-accelerators-biren-106b/20260628T060440806592Z-www-birentech-com-product-hardware-106b-8e22110248.md
  - ../../raw/crawler/compute-accelerators-biren-106m/20260628T060441121627Z-www-birentech-com-product-hardware-106m-bc272ef5f1.md
  - ../../raw/crawler/compute-accelerators-biren-166c/20260628T060441390991Z-www-birentech-com-product-hardware-166c-f3c5e11442.md
  - ../../raw/crawler/compute-accelerators-biren-166l/20260628T060441699966Z-www-birentech-com-product-hardware-166l-93cbb57e8a.md
  - ../../raw/crawler/compute-accelerators-biren-166m/20260628T060441979925Z-www-birentech-com-product-hardware-166m-005ec7f5ac.md
  - ../../raw/crawler/compute-accelerators-resnics-stargate-n1025/20260628T060657022930Z-www-resnics-com-product-stargate-n1025-dpu-8584bb028f.md
  - ../../raw/crawler/compute-accelerators-resnics-stargate-s1100/20260628T060657808728Z-www-resnics-com-product-stargate-s1100-nvme-of-e3a4fe3da7.md
  - ../../raw/crawler/compute-accelerators-corigine-agilio-cx-pdf/20260628T060444859456Z-storage-corigine-com-cn-uploadfiles-pdf-2022-01-24-1-agilio-20cx-202x25gbe-20smartnic-20-e-a138a8aa07.md
  - ../../raw/crawler/compute-accelerators-yusur-k2-pro/20260628T060700357328Z-www-yusur-tech-dpu-k2-pro-c4119da6b0.md
  - ../../raw/crawler/compute-accelerators-yusur-swift-2200n/20260628T060700719790Z-www-yusur-tech-product-swift-swift2200n-7afeac0475.md
  - ../../manifest-ai-infra-expansion-2026-07-07-r9-task-2-gap-proof.json
  - ../../manifest-ai-infra-expansion-2026-07-07-r10-task-2-gap-proof.json
  - ../../manifest-ai-infra-expansion-2026-07-07-r10-task-3-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-1-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-3-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-4-gap-proof.json
---

# Summary

The compute accelerator spec catalog is the structured facts layer for
accelerator parameters in the `ai_infra` domain. It stores sample SKUs,
source-backed observations, and resolved fields with provenance.

# Current Coverage

The seed catalog validates the schema across representative GPU, NPU, TPU,
DPU, IPU, FPGA, DSA, and AI ASIC records. It intentionally leaves incomplete
public fields unresolved instead of inventing missing values.

Continuation parent 4 expands the existing NVIDIA H200 SXM row with the
remaining source-visible, schema-supported single-GPU fields from the local
official H200 product-page capture. H200 SXM now resolves HBM3e memory type,
34 TFLOPS FP64, 67 TFLOPS FP32, 1,979 TFLOPS BFLOAT16, 1,979 TFLOPS FP16,
3,958 TFLOPS FP8, up to 700 W configurable TDP, SXM form factor, and
NVIDIA NVLink 900GB/s plus PCIe Gen5 128GB/s interconnect, while preserving
the existing 141 GB memory and 4.8 TB/s memory-bandwidth rows. H200 NVL
values, TF32, INT8, FP64 Tensor Core, benchmark uplift, MIG, confidential
computing, NVIDIA AI Enterprise bundle, server/system options, H800 runtime
mentions, and Blackwell portfolio pages remain outside this resolved single
H200 SXM slice. [raw](../../raw/crawler/compute-accelerators-nvidia-h200/20260705T041039962650Z-www-nvidia-com-en-us-data-center-h200-a464325a64.md)

R9 task 2 promotes three single-card AI accelerator records from existing
product-specific raw captures into structured SKU, observation, and resolved
spec rows: Cambricon MLU370-X4, Cambricon MLU370-X8, and Kunlunxin RG800. The
resolved fields include INT8, FP16, BF16 where visible, FP32, memory type,
memory capacity, memory bandwidth, host interface, form factor, interconnect
where visible, and power. Multi-variant and aggregate records such as Huawei
Atlas 300I A2, Cambricon MLU370-S4/S8, Kunlunxin R200/R200-8F, R480-X8, and
cloud offerings remain outside this resolved slice unless the source exposes a
single unambiguous card value.

R10 task 2 adds a narrower Biren deployment-envelope slice from existing
product-specific captures. Biren Bili 106B, 106M, 166C, 166L, and 166M now
have structured SKU, observation, and resolved rows for only the source-visible
form factor and peak power fields. Compute, memory, host-interface, and
interconnect values remain unresolved because the local Biren pages do not
expose explicit numeric values for those fields.

R10 task 3 adds a DPU/SmartNIC and storage-offload slice from existing Resnics
product pages. Stargate-N1025 now has resolved form factor, aggregate
source-stated data-port bandwidth, memory capacity, host interface, and typical
power fields. Stargate-S1100 now has resolved host interface, power, 4K/4-SSD
read and write IOPS, and source-stated added-latency upper-bound fields. Broader
Resnics N2025, Asterfusion, Dayu, and Nebula rows remain comparison or
duplicate-boundary evidence unless their exact product or variant boundary is
promoted in a future scoped slice.

The 2026-07-08 continuation parent task promotes one additional local
product-brief slice: Corigine Agilio CX 2x25GbE SmartNIC now has resolved
form factor, aggregate data-port bandwidth, memory type, memory capacity, and
host interface fields. The slice uses only the official PDF product brief and
does not promote power, latency, IOPS, packet-processing, benchmark, or
production-operations claims.

Continuation parent 3 promotes a bounded Yusur DPU slice from existing local
product captures. Yusur K2-Pro now has resolved form factor, 200 Gb/s
source-stated network bandwidth, and `2 x PCIe Gen3 x16` host-interface fields.
Yusur SWIFT-2200N Pro now has a resolved low-latency network DPU card form
factor. The K2-Pro DOE lookup rate, NoC bandwidth and packet rate, NVMe-oF
engine, and unspecified 2M IOPS value stay out of resolved fields because the
catalog has no matching DOE/NoC/generic IOPS fields. The SWIFT PCIe pass-through
latency, loopback latency, and jitter values remain comparison-only because the
schema has no general network-latency or jitter field. [K2-Pro raw](../../raw/crawler/compute-accelerators-yusur-k2-pro/20260628T060700357328Z-www-yusur-tech-dpu-k2-pro-c4119da6b0.md) [SWIFT raw](../../raw/crawler/compute-accelerators-yusur-swift-2200n/20260628T060700719790Z-www-yusur-tech-product-swift-swift2200n-7afeac0475.md)

# Data Flow

Raw evidence and crawler snapshots produce candidate records. Reviewed
candidates become observations. Resolved specs point back to observations and
preserve conflict status, confidence, and update timestamps.

# Validation

Run:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators
```

# Citations

- ../../data/compute_accelerators/README.md
- ../../data/compute_accelerators/skus/sample-skus.yaml
- ../../data/compute_accelerators/observations/sample-observations.yaml
- ../../data/compute_accelerators/resolved/sample-resolved-specs.yaml
- ../../raw/crawler/compute-accelerators-nvidia-h200/20260705T041039962650Z-www-nvidia-com-en-us-data-center-h200-a464325a64.md
- ../../manifest-ai-infra-expansion-continuation-20260708-parent-4-gap-proof.json
- ../../raw/crawler/compute-accelerators-cambricon-mlu370-x4/20260628T060443305596Z-www-cambricon-com-index-php-56612de611.md
- ../../raw/crawler/compute-accelerators-cambricon-mlu370-x8/20260628T060443731999Z-www-cambricon-com-index-php-da315093d5.md
- ../../raw/crawler/compute-accelerators-kunlunxin-rg800/20260628T060652551492Z-www-kunlunxin-com-product-2842-html-6c65e115a3.md
- ../../manifest-ai-infra-expansion-2026-07-07-r9-task-2-gap-proof.json
- ../../raw/crawler/compute-accelerators-biren-106b/20260628T060440806592Z-www-birentech-com-product-hardware-106b-8e22110248.md
- ../../raw/crawler/compute-accelerators-biren-106m/20260628T060441121627Z-www-birentech-com-product-hardware-106m-bc272ef5f1.md
- ../../raw/crawler/compute-accelerators-biren-166c/20260628T060441390991Z-www-birentech-com-product-hardware-166c-f3c5e11442.md
- ../../raw/crawler/compute-accelerators-biren-166l/20260628T060441699966Z-www-birentech-com-product-hardware-166l-93cbb57e8a.md
- ../../raw/crawler/compute-accelerators-biren-166m/20260628T060441979925Z-www-birentech-com-product-hardware-166m-005ec7f5ac.md
- ../../manifest-ai-infra-expansion-2026-07-07-r10-task-2-gap-proof.json
- ../../raw/crawler/compute-accelerators-resnics-stargate-n1025/20260628T060657022930Z-www-resnics-com-product-stargate-n1025-dpu-8584bb028f.md
- ../../raw/crawler/compute-accelerators-resnics-stargate-s1100/20260628T060657808728Z-www-resnics-com-product-stargate-s1100-nvme-of-e3a4fe3da7.md
- ../../manifest-ai-infra-expansion-2026-07-07-r10-task-3-gap-proof.json
- ../../raw/crawler/compute-accelerators-corigine-agilio-cx-pdf/20260628T060444859456Z-storage-corigine-com-cn-uploadfiles-pdf-2022-01-24-1-agilio-20cx-202x25gbe-20smartnic-20-e-a138a8aa07.md
- ../../manifest-ai-infra-expansion-continuation-20260708-parent-1-gap-proof.json
- ../../raw/crawler/compute-accelerators-yusur-k2-pro/20260628T060700357328Z-www-yusur-tech-dpu-k2-pro-c4119da6b0.md
- ../../raw/crawler/compute-accelerators-yusur-swift-2200n/20260628T060700719790Z-www-yusur-tech-product-swift-swift2200n-7afeac0475.md
- ../../manifest-ai-infra-expansion-continuation-20260708-parent-3-gap-proof.json
