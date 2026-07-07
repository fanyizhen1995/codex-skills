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
  - ../../raw/crawler/compute-accelerators-cambricon-mlu370-x4/20260628T060443305596Z-www-cambricon-com-index-php-56612de611.md
  - ../../raw/crawler/compute-accelerators-cambricon-mlu370-x8/20260628T060443731999Z-www-cambricon-com-index-php-da315093d5.md
  - ../../raw/crawler/compute-accelerators-kunlunxin-rg800/20260628T060652551492Z-www-kunlunxin-com-product-2842-html-6c65e115a3.md
  - ../../raw/crawler/compute-accelerators-biren-106b/20260628T060440806592Z-www-birentech-com-product-hardware-106b-8e22110248.md
  - ../../raw/crawler/compute-accelerators-biren-106m/20260628T060441121627Z-www-birentech-com-product-hardware-106m-bc272ef5f1.md
  - ../../raw/crawler/compute-accelerators-biren-166c/20260628T060441390991Z-www-birentech-com-product-hardware-166c-f3c5e11442.md
  - ../../raw/crawler/compute-accelerators-biren-166l/20260628T060441699966Z-www-birentech-com-product-hardware-166l-93cbb57e8a.md
  - ../../raw/crawler/compute-accelerators-biren-166m/20260628T060441979925Z-www-birentech-com-product-hardware-166m-005ec7f5ac.md
  - ../../manifest-ai-infra-expansion-2026-07-07-r9-task-2-gap-proof.json
  - ../../manifest-ai-infra-expansion-2026-07-07-r10-task-2-gap-proof.json
---

# Summary

The compute accelerator spec catalog is the structured facts layer for
accelerator parameters in the `ai_infra` domain. It stores sample SKUs,
source-backed observations, and resolved fields with provenance.

# Current Coverage

The seed catalog validates the schema across representative GPU, NPU, TPU,
DPU, IPU, FPGA, DSA, and AI ASIC records. It intentionally leaves incomplete
public fields unresolved instead of inventing missing values.

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
