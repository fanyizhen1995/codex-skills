---
type: Reference
title: Compute Accelerator Parameter Comparison
description: Current cross-vendor parameter comparison for accelerator, cloud offering, system, DPU, and SmartNIC records captured in ai_infra.
domain: ai_infra
status: reviewed
aliases:
  - accelerator parameter comparison
  - compute card comparison
tags:
  - accelerators
  - specs
  - comparison
source_refs:
  - ../../data/compute_accelerators/skus/sample-skus.yaml
  - ../../data/compute_accelerators/observations/sample-observations.yaml
  - ../../data/compute_accelerators/resolved/sample-resolved-specs.yaml
  - ../../raw/crawler/compute-accelerators-nvidia-h200/20260627T153310569545Z-www-nvidia-com-en-us-data-center-h200-7d05aa2873.md
  - ../../raw/crawler/compute-accelerators-nvidia-h200/20260705T041039962650Z-www-nvidia-com-en-us-data-center-h200-a464325a64.md
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-4-gap-proof.json
  - ../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-rel-2-19-3-html.md
  - ../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-rel-2-18-3-html.md
  - ../../raw/github/nvidia-nccl-closed-issues/api-pages/closed-issues-page-011.json.gz
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/comment-pages/issue-comments-page-205.json.gz
  - ../../raw/crawler/compute-accelerators-aws-trn2/20260627T153315637188Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-17-gap-proof.json
  - ../../raw/crawler/compute-accelerators-nvidia-bluefield-3/20260627T153315013778Z-www-nvidia-com-en-us-networking-products-data-processing-unit-d517920f8d.md
  - ../../raw/crawler/compute-accelerators-huawei-atlas-300i-a2/20260628T055951712859Z-e-huawei-com-cn-products-computing-ascend-atlas-300i-a2-be2af90418.md
  - ../../raw/crawler/compute-accelerators-huawei-atlas-800t-a3/20260628T060648300656Z-e-huawei-com-cn-products-computing-ascend-atlas-800t-a3-4a689659c8.md
  - ../../raw/crawler/compute-accelerators-biren-106b/20260628T060440806592Z-www-birentech-com-product-hardware-106b-8e22110248.md
  - ../../raw/crawler/compute-accelerators-biren-106m/20260628T060441121627Z-www-birentech-com-product-hardware-106m-bc272ef5f1.md
  - ../../raw/crawler/compute-accelerators-biren-166c/20260628T060441390991Z-www-birentech-com-product-hardware-166c-f3c5e11442.md
  - ../../raw/crawler/compute-accelerators-biren-166l/20260628T060441699966Z-www-birentech-com-product-hardware-166l-93cbb57e8a.md
  - ../../raw/crawler/compute-accelerators-biren-166m/20260628T060441979925Z-www-birentech-com-product-hardware-166m-005ec7f5ac.md
  - ../../raw/crawler/compute-accelerators-cambricon-mlu370-s4-s8/20260628T060442871520Z-www-cambricon-com-index-php-dd51e6b9e9.md
  - ../../raw/crawler/compute-accelerators-cambricon-mlu370-x4/20260628T060443305596Z-www-cambricon-com-index-php-56612de611.md
  - ../../raw/crawler/compute-accelerators-cambricon-mlu370-x8/20260628T060443731999Z-www-cambricon-com-index-php-da315093d5.md
  - ../../raw/crawler/compute-accelerators-corigine-agilio-cx-pdf/20260628T060444859456Z-storage-corigine-com-cn-uploadfiles-pdf-2022-01-24-1-agilio-20cx-202x25gbe-20smartnic-20-e-a138a8aa07.md
  - ../../raw/crawler/compute-accelerators-dayu-paratus1/20260628T060445164573Z-www-dayudpu-com-product-paratus1-70c58cfadc.md
  - ../../raw/crawler/compute-accelerators-dayu-paratus2/20260628T060445547733Z-www-dayudpu-com-product-paratus2-24678a2fdd.md
  - ../../raw/crawler/compute-accelerators-denglin-goldwasser-i-l/20260628T060445844413Z-denglinai-com-h-col-252-html-0611810fa3.md
  - ../../raw/crawler/compute-accelerators-denglin-goldwasser-ii-gs/20260628T060446185315Z-denglinai-com-h-col-299-html-8fa5856573.md
  - ../../raw/crawler/compute-accelerators-enflame-cloudblazer-matrix/20260628T060446419609Z-www-enflame-tech-com-cloudblazer-matrix-268-acb13f343e.md
  - ../../raw/crawler/compute-accelerators-enflame-ds-server/20260628T060446676491Z-www-enflame-tech-com-ds-server-c95070751b.md
  - ../../raw/crawler/compute-accelerators-enflame-s60/20260628T060446917641Z-www-enflame-tech-com-s60-7ee9e26bdb.md
  - ../../raw/crawler/compute-accelerators-enflame-sse-disclosure-pdf/20260628T060447599751Z-static-sse-com-cn-stock-disclosure-announcement-c-202604-002175-20260416-wq4o-pdf-08cc50e353.md
  - ../../raw/crawler/compute-accelerators-hygon-dcu/20260628T060648544689Z-www-hygon-cn-product-accelerator-d6c4907bbd.md
  - ../../raw/crawler/compute-accelerators-iluvatar-tg100/20260628T060648884971Z-www-iluvatar-com-productdetails-8c03246db5.md
  - ../../raw/crawler/compute-accelerators-iluvatar-tg150/20260628T060649205621Z-www-iluvatar-com-productdetails-c8a0efc7a3.md
  - ../../raw/crawler/compute-accelerators-iluvatar-zk100/20260628T060649509748Z-www-iluvatar-com-productdetails-9cf9c89ce3.md
  - ../../raw/crawler/compute-accelerators-intel-gaudi-3/20260627T153313974904Z-www-intel-com-content-www-us-en-content-details-817486-intel-gaudi-3-ai-accelerator-white-72421ce95f.md
  - ../../raw/crawler/compute-accelerators-jaguarmicro-yunxiao-dpu/20260628T060651455844Z-www-jaguarmicro-com-n4-html-87a5670154.md
  - ../../raw/crawler/compute-accelerators-kunlunxin-r200/20260628T060651804777Z-www-kunlunxin-com-product-274-html-d12bf3953a.md
  - ../../raw/crawler/compute-accelerators-kunlunxin-r480-x8/20260628T060652154506Z-www-kunlunxin-com-product-272-html-89686dc880.md
  - ../../raw/crawler/compute-accelerators-kunlunxin-rg800/20260628T060652551492Z-www-kunlunxin-com-product-2842-html-6c65e115a3.md
  - ../../raw/crawler/compute-accelerators-metax-c500/20260628T060652781059Z-www-metax-tech-com-prod-html-8de5962075.md
  - ../../raw/crawler/compute-accelerators-metax-c500x/20260628T060653016639Z-www-metax-tech-com-prod-html-51b80e7359.md
  - ../../raw/crawler/compute-accelerators-metax-c550/20260628T060653231697Z-www-metax-tech-com-prod-html-ea84ef2c6c.md
  - ../../raw/crawler/compute-accelerators-metax-c588/20260628T060653452377Z-www-metax-tech-com-prod-html-9d84457b12.md
  - ../../raw/crawler/compute-accelerators-metax-c600/20260628T060653669535Z-www-metax-tech-com-prod-html-259649e029.md
  - ../../raw/crawler/compute-accelerators-mthreads-s3000/20260628T060654703690Z-www-mthreads-com-product-s3000-28c8f7773e.md
  - ../../raw/crawler/compute-accelerators-mthreads-s4000/20260628T060655050600Z-www-mthreads-com-product-s4000-e4c4564f49.md
  - ../../raw/crawler/compute-accelerators-mthreads-s5000/20260628T060655366010Z-www-mthreads-com-product-s5000-50b13e9e39.md
  - ../../raw/crawler/compute-accelerators-nebula-dpu200/20260628T060655740838Z-www-nebula-matrix-com-dpu200-7e44cc4782.md
  - ../../raw/crawler/compute-accelerators-nebula-rnic-ip/20260628T060656128184Z-www-nebula-matrix-com-rnic-ip-6a2d630a55.md
  - ../../raw/crawler/compute-accelerators-nebula-snic-s1400/20260628T060656459873Z-www-nebula-matrix-com-snic-s1400-3a683422fd.md
  - ../../raw/crawler/compute-accelerators-nvidia-gb300/20260628T143110957451Z-www-nvidia-com-en-us-data-center-products-200b75abd8.md
  - ../../raw/crawler/compute-accelerators-resnics-stargate-n1025/20260628T060657022930Z-www-resnics-com-product-stargate-n1025-dpu-8584bb028f.md
  - ../../raw/crawler/compute-accelerators-resnics-stargate-n2025/20260628T060657411423Z-www-resnics-com-product-stargate-n2025-dpu-f2feeec038.md
  - ../../raw/crawler/compute-accelerators-resnics-stargate-s1100/20260628T060657808728Z-www-resnics-com-product-stargate-s1100-nvme-of-e3a4fe3da7.md
  - ../../raw/crawler/compute-accelerators-vastaitech-va1/20260628T060658419245Z-www-vastaitech-com-product-general-va1-e80df13a88.md
  - ../../raw/crawler/compute-accelerators-vastaitech-va10/20260628T060659001491Z-www-vastaitech-com-product-general-va10-0a749592fe.md
  - ../../raw/crawler/compute-accelerators-yusur-k2-pro/20260628T060700357328Z-www-yusur-tech-dpu-k2-pro-c4119da6b0.md
  - ../../raw/crawler/compute-accelerators-yusur-swift-2200n/20260628T060700719790Z-www-yusur-tech-product-swift-swift2200n-7afeac0475.md
  - ../../raw/crawler/compute-accelerator-discovery-amd-instinct/20260706T203709866943Z-www-amd-com-en-products-accelerators-instinct-html-d416b602fe.md
  - ../../raw/crawler/compute-accelerators-amd-mi350p/20260706T204115675975Z-www-amd-com-en-products-accelerators-instinct-html-d416b602fe.md
  - ../../raw/crawler/compute-accelerators-biren-106b/20260706T204117808018Z-www-birentech-com-product-hardware-106b-b7fa1c7a80.md
  - ../../raw/crawler/compute-accelerators-biren-106m/20260706T204118104735Z-www-birentech-com-product-hardware-106m-65554c3ddd.md
  - ../../raw/crawler/compute-accelerators-biren-166l/20260706T204118518475Z-www-birentech-com-product-hardware-166l-f208dc4baf.md
  - ../../raw/crawler/compute-accelerators-biren-166m/20260706T204118823905Z-www-birentech-com-product-hardware-166m-01b6a2d386.md
  - ../../raw/crawler/compute-accelerators-cambricon-mlu370-s4-s8/20260706T204119753429Z-www-cambricon-com-index-php-dd51e6b9e9.md
  - ../../raw/crawler/compute-accelerators-cambricon-mlu370-x8/20260706T204120148067Z-www-cambricon-com-index-php-da315093d5.md
  - ../../raw/crawler/compute-accelerators-corigine-agilio-cx-pdf/20260706T204120429357Z-storage-corigine-com-cn-uploadfiles-pdf-2022-01-24-1-agilio-20cx-202x25gbe-20smartnic-20-e-a138a8aa07.md
  - ../../raw/crawler/compute-accelerators-asterfusion-helium-dpu/20260706T204116820726Z-asterfusion-com-product-helium-dpu-121181ec67.md
  - ../../raw/crawler/compute-accelerators-asterfusion-cx102s-dpu/20260706T204116541565Z-asterfusion-com-product-cx102s-dpu-b77dd4635a.md
  - ../../raw/crawler/compute-accelerators-enflame-s60/20260706T204121967738Z-www-enflame-tech-com-7d7fdd552a.md
  - ../../manifest-ai-infra-expansion-2026-07-07-r9-task-2-gap-proof.json
  - ../../manifest-ai-infra-expansion-2026-07-07-r10-task-2-gap-proof.json
  - ../../manifest-ai-infra-expansion-2026-07-07-r10-task-3-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-1-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-3-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-7-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-9-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-10-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-11-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-12-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-14-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-15-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-18-gap-proof.json
  - ../../manifest-ai-infra-expansion-continuation-20260708-parent-19-gap-proof.json
---

# Summary

This page compares every compute-accelerator record currently represented in
the local `ai_infra` structured catalog or captured under
`raw/crawler/compute-accelerators-*`. The comparison is evidence-scoped: if a
field is not visible in the local wiki/raw evidence, it is marked as not
captured instead of inferred.

Use the structured catalog rows as resolved fields. Use the crawler rows as a
source-backed reading list for fields that still need observation/resolution
before becoming normalized catalog facts.

# Comparison Notes

- Single accelerator cards/modules can be compared on memory, bandwidth,
  tensor/INT8 performance, host interface, interconnect, and power.
- Cloud offerings and systems are aggregate configurations. Do not compare AWS
  Trn2, Huawei Atlas 800T A3, or Kunlunxin R480-X8 directly with one PCIe card
  without normalizing by chip/card count.
- DPU, IPU, and SmartNIC records are infrastructure accelerators. Compare them
  on network rate, offload engines, PCIe generation, memory, IOPS, and latency
  rather than FLOPS.

# 20260706 Baseline Reconciliation

The July 6 tracked baseline is a refresh of existing compute accelerator source profiles, not a new standalone catalog. It removes the former unreconciled-baseline boundary for `raw/crawler/compute-*20260706*`, but it does not relax the evidence rule: a field is promoted only when a product-specific page, table, datasheet, PDF, or comparable source exposes an unambiguous value.

| July 6 capture group | Reconciliation action |
| --- | --- |
| AMD Instinct and Alveo refreshes | Track as portfolio/source-monitoring evidence. The local July text advertises MI350/MI300/MI200 and Alveo families, but the task does not promote per-SKU numeric fields from the portfolio pages. [AMD Instinct discovery](../../raw/crawler/compute-accelerator-discovery-amd-instinct/20260706T203709866943Z-www-amd-com-en-products-accelerators-instinct-html-d416b602fe.md), [MI350P source profile](../../raw/crawler/compute-accelerators-amd-mi350p/20260706T204115675975Z-www-amd-com-en-products-accelerators-instinct-html-d416b602fe.md) |
| Biren 106B, 106M, 166L, and 166M | Refresh existing form-factor and peak-power rows; no new compute or memory fields are added because the visible local text still does not expose those values. [106B](../../raw/crawler/compute-accelerators-biren-106b/20260706T204117808018Z-www-birentech-com-product-hardware-106b-b7fa1c7a80.md), [106M](../../raw/crawler/compute-accelerators-biren-106m/20260706T204118104735Z-www-birentech-com-product-hardware-106m-65554c3ddd.md), [166L](../../raw/crawler/compute-accelerators-biren-166l/20260706T204118518475Z-www-birentech-com-product-hardware-166l-f208dc4baf.md), [166M](../../raw/crawler/compute-accelerators-biren-166m/20260706T204118823905Z-www-birentech-com-product-hardware-166m-01b6a2d386.md) |
| Cambricon MLU370-S4/S8 and MLU370-X8 | Exact content-hash refreshes for already-curated product tables. Existing compute, memory, interface, and power rows remain source-backed and require no duplicate row. [S4/S8](../../raw/crawler/compute-accelerators-cambricon-mlu370-s4-s8/20260706T204119753429Z-www-cambricon-com-index-php-dd51e6b9e9.md), [X8](../../raw/crawler/compute-accelerators-cambricon-mlu370-x8/20260706T204120148067Z-www-cambricon-com-index-php-da315093d5.md) |
| Corigine Agilio CX PDF and Asterfusion DPU captures | Corigine is promoted as a bounded structured SmartNIC slice from the official product brief. Parent 9 promotes only the source-visible Asterfusion subset that fits the catalog schema: Helium form factor, mixed-service 100 Gb/s capability, expandable memory, PCIe host interface, source comparison power, and CX102S module memory; Helium port variants and CX102S gateway capacity remain boundary evidence. [Corigine](../../raw/crawler/compute-accelerators-corigine-agilio-cx-pdf/20260706T204120429357Z-storage-corigine-com-cn-uploadfiles-pdf-2022-01-24-1-agilio-20cx-202x25gbe-20smartnic-20-e-a138a8aa07.md), [Asterfusion Helium](../../raw/crawler/compute-accelerators-asterfusion-helium-dpu/20260706T204116820726Z-asterfusion-com-product-helium-dpu-121181ec67.md), [Asterfusion CX102S](../../raw/crawler/compute-accelerators-asterfusion-cx102s-dpu/20260706T204116541565Z-asterfusion-com-product-cx102s-dpu-b77dd4635a.md) |
| Enflame S60 July capture | Intentionally not used to replace the older S60-specific citation because the July capture resolves to the Enflame homepage and does not expose the old PCIe 5.0 field in local text. [July homepage capture](../../raw/crawler/compute-accelerators-enflame-s60/20260706T204121967738Z-www-enflame-tech-com-7d7fdd552a.md) |

# Quick Read

- Highest single-accelerator memory captured in the structured catalog:
  AMD Instinct MI325X at 256 GB, followed by NVIDIA H200 SXM at 141 GB and
  Intel Gaudi 3 HL-338 at 128 GB. Continuation parent 4 now resolves H200 SXM
  HBM3e memory type, FP64, FP32, BF16, FP16, FP8, configurable TDP, SXM form
  factor, and NVLink/PCIe Gen5 interconnect fields while keeping TF32, INT8,
  H200 NVL, benchmarks, and server/system claims out of the single-GPU
  resolved row. R9 task 2 adds source-backed structured rows for Cambricon
  MLU370-X4, Cambricon MLU370-X8, and Kunlunxin RG800, including compute,
  memory, host-interface, form-factor, and power fields. Continuation parent 10
  adds Kunlunxin R200 and R200-8F resolved rows for schema-supported compute,
  memory, host-interface, form-factor, and power fields while leaving INT16 as
  raw comparison evidence. Continuation parent 11 adds Iluvatar Tiangai 100
  resolved fields for form factor, 32 GB HBM2, `PCIe Gen4.0 x16 lane`,
  source-stated 64 GB/s inter-chip bandwidth, and 250 W board power, plus
  Tiangai 150 resolved fields for 64 GB HBM memory and 350 W board power only.
  Continuation parent 19 adds distinct Iluvatar Zhikai 50 and Zhikai 100 rows
  for only the source-visible form factor, HBM2E memory capacity/type, PCIe
  Gen4.0 x16 host interface, and board-power fields.
  Continuation parent 12 adds MetaX C500, C500X, C550, and C588 resolved rows
  for source-visible form factor, memory capacity, MetaXLink interconnect
  wording, and maximum power only; continuation parent 13 adds MetaX C600
  resolved rows for OAM 2.0 form factor, MetaXLink/MetaXLink-E interconnect
  wording, and 1000 W maximum power only. R10 task 2 adds Biren Bili 106B, 106M, 166C,
  166L, and 166M form-factor and peak power fields only; compute and memory
  remain unresolved for those Biren rows.
  [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml)
- Clearest high-end single-GPU raw record: NVIDIA H200 SXM/H200 NVL. The
  structured catalog resolves only the H200 SXM column for schema-supported
  fields; the H200 NVL column, TF32 row, INT8 row with incompatible catalog
  unit boundary, benchmark speedups, server options, MIG, confidential
  computing, and NVIDIA AI Enterprise bundle text remain comparison or boundary
  evidence. [raw](../../raw/crawler/compute-accelerators-nvidia-h200/20260705T041039962650Z-www-nvidia-com-en-us-data-center-h200-a464325a64.md)
- NVIDIA H800 is present in local runtime and release-note evidence, but not as
  a resolved product-spec record. The local evidence supports only limited
  facts: NCCL groups H800 with H100 as Hopper GPUs, one NCCL issue log reports
  `H800 SXM5` devices named `NVIDIA H800`, and one SGLang issue comment reports
  an 8 x NVIDIA H800 environment with CUDA compute capability 9.0 and NV18
  intra-node GPU topology. Do not infer memory capacity, memory bandwidth,
  tensor FLOPS, power, or host-interface parameters from these runtime logs.
  [NCCL 2.19.3](../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-rel-2-19-3-html.md),
  [NCCL issue page](../../raw/github/nvidia-nccl-closed-issues/api-pages/closed-issues-page-011.json.gz),
  [SGLang comment page](../../raw/github/sgl-project-sglang-closed-issues-prs/comment-pages/issue-comments-page-205.json.gz)
- Strong domestic card/module-level comparison set: Huawei Atlas 300I A2,
  Cambricon MLU370, Kunlunxin R200/R200-8F/RG800, Iluvatar Tiangai 100,
  Iluvatar Zhikai 50/100, and the
  MetaX C500/C500X/C550/C588 pages expose enough local raw parameters to compare
  some compute, deployment-envelope, memory-capacity, memory-bandwidth,
  host-interface, interconnect-wording, and power fields as individual products.
  Continuation parent 14 now resolves Huawei Atlas 300I A2 as separate 32 GB and
  64 GB memory variants; C600 exposes only deployment envelope,
  interconnect wording, and maximum power as resolved fields; the Kunlunxin and
  Cambricon rows also expose source-visible compute values. Tiangai 150 contributes only memory and
  board-power resolved fields from the local page, so do not compare its
  compute, memory bandwidth, form factor, or host interface without a stronger
  source. The MetaX rows do not resolve compute, memory generation, memory
  bandwidth, host-interface lane count, virtualization, server, supernode,
  benchmark, production-operation, or ecosystem-completion claims; C600 also
  does not resolve memory capacity or memory type from qualitative memory text. R200/R200-8F
  and RG800 now have structured resolved rows for schema-supported fields; INT16
  remains comparison-only. Zhikai FP32/FP16/INT8 support, video/image codec
  capacity, CUDA compatibility, migration-time, performance-ratio,
  instruction-set, cost, application-scenario, benchmark, production-operation,
  service-SLO, and ranking text remains comparison-only boundary evidence.
  [Atlas 300I A2](../../raw/crawler/compute-accelerators-huawei-atlas-300i-a2/20260628T055951712859Z-e-huawei-com-cn-products-computing-ascend-atlas-300i-a2-be2af90418.md),
  [MLU370-S4/S8](../../raw/crawler/compute-accelerators-cambricon-mlu370-s4-s8/20260628T060442871520Z-www-cambricon-com-index-php-dd51e6b9e9.md),
  [MLU370-X4](../../raw/crawler/compute-accelerators-cambricon-mlu370-x4/20260628T060443305596Z-www-cambricon-com-index-php-56612de611.md),
  [MLU370-X8](../../raw/crawler/compute-accelerators-cambricon-mlu370-x8/20260628T060443731999Z-www-cambricon-com-index-php-da315093d5.md),
  [R200](../../raw/crawler/compute-accelerators-kunlunxin-r200/20260628T060651804777Z-www-kunlunxin-com-product-274-html-d12bf3953a.md),
  [RG800](../../raw/crawler/compute-accelerators-kunlunxin-rg800/20260628T060652551492Z-www-kunlunxin-com-product-2842-html-6c65e115a3.md),
  [Tiangai 100](../../raw/crawler/compute-accelerators-iluvatar-tg100/20260628T060648884971Z-www-iluvatar-com-productdetails-8c03246db5.md),
  [Tiangai 150](../../raw/crawler/compute-accelerators-iluvatar-tg150/20260628T060649205621Z-www-iluvatar-com-productdetails-c8a0efc7a3.md),
  [Zhikai 50/100](../../raw/crawler/compute-accelerators-iluvatar-zk100/20260628T060649509748Z-www-iluvatar-com-productdetails-9cf9c89ce3.md),
  [MetaX C500](../../raw/crawler/compute-accelerators-metax-c500/20260628T060652781059Z-www-metax-tech-com-prod-html-8de5962075.md),
  [MetaX C500X](../../raw/crawler/compute-accelerators-metax-c500x/20260628T060653016639Z-www-metax-tech-com-prod-html-51b80e7359.md),
  [MetaX C550](../../raw/crawler/compute-accelerators-metax-c550/20260628T060653231697Z-www-metax-tech-com-prod-html-ea84ef2c6c.md),
  [MetaX C588](../../raw/crawler/compute-accelerators-metax-c588/20260628T060653452377Z-www-metax-tech-com-prod-html-9d84457b12.md),
  [MetaX C600](../../raw/crawler/compute-accelerators-metax-c600/20260628T060653669535Z-www-metax-tech-com-prod-html-259649e029.md)
- Aggregate records must be normalized before card-to-card comparison: AWS
  Trn2/UltraServer, Huawei Atlas 800T A3, and Kunlunxin R480-X8 report
  multi-chip or system-level totals. The structured catalog resolves only the
  Trn2 instance cloud offering count and aggregate accelerator memory:
  16 Trainium2 chips and 1536 GB accelerator memory for `trn2.48xlarge` and
  `trn2u.48xlarge`. UltraServer 6 TB memory and aggregate compute/bandwidth
  remain comparison-only boundary evidence. Use these rows for capacity
  planning, not as direct single-card substitutes. [AWS Trn2](../../raw/crawler/compute-accelerators-aws-trn2/20260627T153315637188Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md),
  [Atlas 800T A3](../../raw/crawler/compute-accelerators-huawei-atlas-800t-a3/20260628T060648300656Z-e-huawei-com-cn-products-computing-ascend-atlas-800t-a3-4a689659c8.md),
  [R480-X8](../../raw/crawler/compute-accelerators-kunlunxin-r480-x8/20260628T060652154506Z-www-kunlunxin-com-product-272-html-89686dc880.md)
- DPU/SmartNIC records are not FLOPS peers. NVIDIA BlueField-3, NVIDIA
  BlueField-4, Asterfusion Helium, Resnics Stargate, Yusur K2-Pro, Yusur
  SWIFT-2200N Pro, and Corigine
  Agilio are better compared by line rate, packet/storage offload, PCIe
  generation, memory, IOPS, and latency. The structured catalog now resolves
  Corigine Agilio CX 2x25GbE SmartNIC for form factor, aggregate 50 Gb/s
  data-port bandwidth, 2 GB DDR3 onboard memory, and PCIe Base 3.0 x8
  host-interface wording; it also resolves Yusur K2-Pro form factor, 200 Gb/s
  source-stated network bandwidth, `2 x PCIe Gen3 x16` host interface, and the
  SWIFT-2200N Pro low-latency DPU-card form factor. Continuation parent 7
  resolves Resnics Stargate-N2025 form factor, aggregate 50 Gb/s data-port
  bandwidth, split-pool DDR4 memory capacity, `PCIe Gen4 x8`, and 150 W power
  while leaving SR-IOV, RDMA, P4 table, protocol, storage-offload, benchmark,
  and production-operation values as comparison-only boundary evidence.
  Continuation parent 18 adds only BlueField-4 DPU `network_bandwidth=800 Gb/s`
  from the source-stated `800Gb/s infrastructure platform` portfolio entry;
  BlueField-4 STX, CMX/context-memory storage, cybersecurity, threat-detection,
  benchmark, production-operation, service-SLO, ecosystem, storage throughput,
  memory, host-interface, and compute text stays out of structured catalog
  fields.
  [BlueField-3](../../raw/crawler/compute-accelerators-nvidia-bluefield-3/20260627T153315013778Z-www-nvidia-com-en-us-networking-products-data-processing-unit-d517920f8d.md),
  [Asterfusion Helium](../../raw/crawler/compute-accelerators-asterfusion-helium-dpu/20260628T060438266386Z-asterfusion-com-product-helium-dpu-121181ec67.md),
  [Resnics Stargate-N2025](../../raw/crawler/compute-accelerators-resnics-stargate-n2025/20260628T060657411423Z-www-resnics-com-product-stargate-n2025-dpu-f2feeec038.md),
  [Resnics Stargate-S1100](../../raw/crawler/compute-accelerators-resnics-stargate-s1100/20260628T060657808728Z-www-resnics-com-product-stargate-s1100-nvme-of-e3a4fe3da7.md),
  [Yusur K2-Pro](../../raw/crawler/compute-accelerators-yusur-k2-pro/20260628T060700357328Z-www-yusur-tech-dpu-k2-pro-c4119da6b0.md),
  [Yusur SWIFT-2200N Pro](../../raw/crawler/compute-accelerators-yusur-swift-2200n/20260628T060700719790Z-www-yusur-tech-product-swift-swift2200n-7afeac0475.md),
  [Corigine Agilio CX](../../raw/crawler/compute-accelerators-corigine-agilio-cx-pdf/20260628T060444859456Z-storage-corigine-com-cn-uploadfiles-pdf-2022-01-24-1-agilio-20cx-202x25gbe-20smartnic-20-e-a138a8aa07.md)

# Resolved Catalog Fields

| Record | Type | Resolved parameters | Citation |
| --- | --- | --- | --- |
| NVIDIA H200 SXM | GPU module | 141 GB HBM3e; 4.8 TB/s memory bandwidth; 34 TFLOPS FP64; 67 TFLOPS FP32; 1,979 TFLOPS BF16; 1,979 TFLOPS FP16; 3,958 TFLOPS FP8; up to 700 W configurable TDP; SXM form factor; NVIDIA NVLink 900GB/s and PCIe Gen5 128GB/s interconnect | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-nvidia-h200/20260705T041039962650Z-www-nvidia-com-en-us-data-center-h200-a464325a64.md) |
| AMD Instinct MI325X | GPU module | 256 GB memory | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml) |
| Intel Gaudi 3 HL-338 | AI ASIC / PCIe card | 128 GB memory | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml) |
| NXP i.MX 95 eIQ Neutron NPU | integrated SoC NPU | integrated SoC NPU form factor | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml) |
| NVIDIA BlueField-3 DPU | DPU | 400 Gb/s network bandwidth | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml) |
| NVIDIA BlueField-4 DPU | DPU | 800 Gb/s network bandwidth | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-nvidia-bluefield-3/20260627T153315013778Z-www-nvidia-com-en-us-networking-products-data-processing-unit-d517920f8d.md) |
| AWS Trainium2 Trn2 offering | cloud AI ASIC offering | 16 accelerators and 1536 GB aggregate accelerator memory per `trn2.48xlarge` / `trn2u.48xlarge` offering | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-aws-trn2/20260627T153315637188Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md) |
| Google Cloud TPU v5p offering | cloud TPU offering | cloud offering form factor | [observations](../../data/compute_accelerators/observations/sample-observations.yaml) |
| AMD Alveo V80 | FPGA / PCIe card | no resolved parameter yet | [SKUs](../../data/compute_accelerators/skus/sample-skus.yaml) |
| Intel IPU Adapter E2100 | IPU / PCIe card | 200 Gb/s network bandwidth | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml) |
| Microsoft Maia 200 | cloud-integrated DSA | 216 GB memory; 7 TB/s memory bandwidth | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml) |
| Huawei Atlas 300I A2 32 GB | NPU / PCIe card | dual-slot full-height full-length PCIe card; 560 TOPS INT8; 280 TFLOPS FP16; 32 GB on-card memory; 0.8 TB/s memory bandwidth; PCIe 5.0; 350 W maximum power | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-huawei-atlas-300i-a2/20260628T055951712859Z-e-huawei-com-cn-products-computing-ascend-atlas-300i-a2-be2af90418.md) |
| Huawei Atlas 300I A2 64 GB | NPU / PCIe card | dual-slot full-height full-length PCIe card; 560 TOPS INT8; 280 TFLOPS FP16; 64 GB on-card memory; 1.6 TB/s memory bandwidth; PCIe 5.0; 350 W maximum power | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-huawei-atlas-300i-a2/20260628T055951712859Z-e-huawei-com-cn-products-computing-ascend-atlas-300i-a2-be2af90418.md) |
| Cambricon MLU370-X4 | AI ASIC / PCIe card | 256 TOPS INT8; 96 TFLOPS FP16; 96 TFLOPS BF16; 24 TFLOPS FP32; 24 GB LPDDR5; 307.2 GB/s memory bandwidth; x16 PCIe Gen4; 150 W; full-height full-length single-slot card | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-cambricon-mlu370-x4/20260628T060443305596Z-www-cambricon-com-index-php-56612de611.md) |
| Cambricon MLU370-X8 | AI ASIC / PCIe card | 256 TOPS INT8; 96 TFLOPS FP16; 96 TFLOPS BF16; 24 TFLOPS FP32; 48 GB LPDDR5; 614.4 GB/s memory bandwidth; x16 PCIe Gen4; MLU-Link 200 GB/s bidirectional aggregate; 250 W; full-height full-length dual-slot card | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-cambricon-mlu370-x8/20260628T060443731999Z-www-cambricon-com-index-php-da315093d5.md) |
| Kunlunxin RG800 | AI ASIC / PCIe card | 256 TOPS INT8; 128 TFLOPS FP16; 32 TFLOPS FP32; 32 GB GDDR6; 512 GB/s memory bandwidth; PCIe 4.0 x16; 130 W; full-height full-length single-slot card | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-kunlunxin-rg800/20260628T060652551492Z-www-kunlunxin-com-product-2842-html-6c65e115a3.md) |
| Iluvatar Tiangai 100 | GPU / PCIe card | full-length full-height dual-slot PCIe card; 32 GB HBM2; PCIe Gen4.0 x16 lane; source-stated 64 GB/s inter-chip bandwidth; 250 W board power | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-iluvatar-tg100/20260628T060648884971Z-www-iluvatar-com-productdetails-8c03246db5.md) |
| Iluvatar Tiangai 150 | GPU / training accelerator | 64 GB HBM memory; 350 W board power. Exact compute peaks, memory bandwidth, form factor, host interface, and benchmark claims are not resolved from the local page. | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-iluvatar-tg150/20260628T060649205621Z-www-iluvatar-com-productdetails-c8a0efc7a3.md) |
| Iluvatar Zhikai 50 | GPU / PCIe inference card | half-length half-height single-slot PCIe card; 16 GB HBM2E; PCIe Gen4.0 x16 lane; 75 W board power. FP32/FP16/INT8 support, codec capacity, CUDA compatibility, migration-time, performance-ratio, instruction-set, application, cost, benchmark, operation, SLO, and ranking claims are not resolved. | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-iluvatar-zk100/20260628T060649509748Z-www-iluvatar-com-productdetails-9cf9c89ce3.md) |
| Iluvatar Zhikai 100 | GPU / PCIe inference card | full-length full-height single-slot PCIe card; 32 GB HBM2E; PCIe Gen4.0 x16 lane; 150 W board power. FP32/FP16/INT8 support, codec capacity, CUDA compatibility, migration-time, performance-ratio, instruction-set, application, cost, benchmark, operation, SLO, and ranking claims are not resolved. | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-iluvatar-zk100/20260628T060649509748Z-www-iluvatar-com-productdetails-9cf9c89ce3.md) |
| Biren Bili 106B | AI ASIC / PCIe card | full-height full-length double-wide PCIe card; 300 W peak power | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-biren-106b/20260628T060440806592Z-www-birentech-com-product-hardware-106b-8e22110248.md) |
| Biren Bili 106M | AI ASIC / OAM module | air-cooled OAM module; 400 W peak power | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-biren-106m/20260628T060441121627Z-www-birentech-com-product-hardware-106m-bc272ef5f1.md) |
| Biren Bili 166C | AI ASIC / PCIe card | full-height full-length 290 mm double-wide PCIe inference card; 300 W peak power | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-biren-166c/20260628T060441390991Z-www-birentech-com-product-hardware-166c-f3c5e11442.md) |
| Biren Bili 166L | AI ASIC / OAM module | cold-plate liquid-cooled OAM module; 600 W peak power | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-biren-166l/20260628T060441699966Z-www-birentech-com-product-hardware-166l-93cbb57e8a.md) |
| Biren Bili 166M | AI ASIC / OAM module | 4U OAM V1.1 air-cooled module; 550 W peak power | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-biren-166m/20260628T060441979925Z-www-birentech-com-product-hardware-166m-005ec7f5ac.md) |
| Corigine Agilio CX 2x25GbE SmartNIC | DPU / SmartNIC card | 2 x 25GbE SmartNIC card; aggregate 50 Gb/s data-port bandwidth; 2 GB DDR3 onboard memory; PCIe Base 3.0 compatible with PCIe 1.1/2.0, x8 link | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-corigine-agilio-cx-pdf/20260628T060444859456Z-storage-corigine-com-cn-uploadfiles-pdf-2022-01-24-1-agilio-20cx-202x25gbe-20smartnic-20-e-a138a8aa07.md) |
| Resnics Stargate-N2025 | DPU / SmartNIC card | full-height double-wide three-quarter-length PCIe card; aggregate 50 Gb/s data-port bandwidth; 24 GB aggregate visible DDR4 capacity from 8 GB FPGA logic memory plus 16 GB SoC logic memory; PCIe Gen4 x8; 150 W | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-resnics-stargate-n2025/20260628T060657411423Z-www-resnics-com-product-stargate-n2025-dpu-f2feeec038.md) |
| Yusur K2-Pro DPU | DPU chip / product-series DPU | DPU chip / product-series DPU; 200 Gb/s source-stated network bandwidth; 2 x PCIe Gen3 x16 host interface | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-yusur-k2-pro/20260628T060700357328Z-www-yusur-tech-dpu-k2-pro-c4119da6b0.md) |
| Yusur SWIFT-2200N Pro | DPU / low-latency network card | low-latency network DPU card form factor; latency and jitter values remain comparison-only schema-boundary evidence | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-yusur-swift-2200n/20260628T060700719790Z-www-yusur-tech-product-swift-swift2200n-7afeac0475.md) |
| Asterfusion Helium DPU SmartNIC | DPU / PCIe SmartNIC | PCIe DPU SmartNIC; 100 Gb/s source-stated mixed-service processing capability; expandable 64 GB memory; PCIe x8 Gen3.0/4.0 host interface; 60 W source comparison power | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-asterfusion-helium-dpu/20260706T204116820726Z-asterfusion-com-product-helium-dpu-121181ec67.md) |
| Asterfusion CX102S-DPU Module | DPU module inside 1U gateway | DPU module inside a 1U open intelligent gateway; 8 GB DDR4 module memory; 72 Gb/s switching capacity and 16 x 1GE plus 2 x 10GE gateway ports remain gateway-level comparison evidence | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-asterfusion-cx102s-dpu/20260706T204116541565Z-asterfusion-com-product-cx102s-dpu-b77dd4635a.md) |
| JaguarMicro Yunxiao DPU | DPU product | aggregate 50 Gb/s Ethernet bandwidth from source-visible 2 x 25G text; protocol, virtualization, security, QoS, elastic storage/network, hot migration, hot upgrade, memory, host-interface, power, benchmark, and production-operation text remains boundary evidence | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-jaguarmicro-yunxiao-dpu/20260628T060651455844Z-www-jaguarmicro-com-n4-html-87a5670154.md) |

# Unresolved Runtime Evidence

| Record | Evidence status | Locally supported facts | Not locally resolved | Citation |
| --- | --- | --- | --- | --- |
| NVIDIA H800 | Runtime and release-note evidence only; no product-spec or resolved catalog row captured | Hopper-class GPU grouping in NCCL release notes; observed as `H800 SXM5` / `NVIDIA H800` in an NCCL issue log; one SGLang issue comment reports 8 x NVIDIA H800 with CUDA compute capability 9.0 and NV18 intra-node GPU topology | Memory capacity, memory bandwidth, tensor/INT8/FP64/FP32 performance, power, host interface, and official NVLink bandwidth | [NCCL 2.19.3](../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-rel-2-19-3-html.md), [NCCL 2.18.3](../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-rel-2-18-3-html.md), [NCCL issue API page](../../raw/github/nvidia-nccl-closed-issues/api-pages/closed-issues-page-011.json.gz), [SGLang issue comment API page](../../raw/github/sgl-project-sglang-closed-issues-prs/comment-pages/issue-comments-page-205.json.gz) |

# AI Accelerator And System Raw Comparison

| Record | Form | Compute | Memory and bandwidth | Power / interface / interconnect | Citation |
| --- | --- | --- | --- | --- | --- |
| NVIDIA H200 SXM / H200 NVL | SXM module / PCIe dual-slot air-cooled | H200 SXM: FP64 34 TFLOPS, FP32 67 TFLOPS, TF32 989 TFLOPS, BF16/FP16 1,979 TFLOPS, FP8/INT8 3,958 TFLOPS; H200 NVL: FP64 30 TFLOPS, FP32 60 TFLOPS, BF16/FP16 1,671 TFLOPS, FP8/INT8 3,341 TFLOPS. Only H200 SXM FP64, FP32, BF16, FP16, and FP8 are resolved; TF32 lacks a catalog field and INT8 stays out because the source row uses the incompatible TFLOPS wording for the catalog's TOPS field. | 141 GB HBM3e; 4.8 TB/s | SXM up to 700 W; NVL up to 600 W; H200 SXM interconnect row lists NVIDIA NVLink 900GB/s and PCIe Gen5 128GB/s | [raw](../../raw/crawler/compute-accelerators-nvidia-h200/20260705T041039962650Z-www-nvidia-com-en-us-data-center-h200-a464325a64.md) |
| AWS Trainium2 Trn2 / Trn2 UltraServer | cloud offering | Trn2 instance: up to 20.8 FP8 PFLOPS; UltraServer: up to 83.2 FP8 PFLOPS. Aggregate compute is comparison-only, not `fp8_tflops`. | Trn2: resolved cloud-offering aggregate memory is 1536 GB from the source-stated 1.5 TB HBM3; 46 TBps total memory bandwidth remains comparison-only. UltraServer: 6 TB HBM and 185 TBps total bandwidth remain boundary evidence. | Trn2: 16 Trainium2 chips and 3.2 Tbps EFAv3; UltraServer: 64 chips and 12.8 Tbps EFAv3. EFAv3 remains cloud-fabric evidence, not `network_bandwidth`. | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-aws-trn2/20260627T153315637188Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md) |
| Huawei Atlas 300I A2 | dual-slot full-height full-length PCIe inference card | 560 TOPS INT8; 280 TFLOPS FP16; CPU text is source-visible but not promoted | Resolved as two memory variants: 32 GB at 0.8 TB/s, and 64 GB at 1.6 TB/s on-card memory | PCIe 5.0; maximum 350 W. Passive air cooling, fan modules, operating temperature, and dimensions remain source-visible boundary evidence, not resolved catalog fields. | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-huawei-atlas-300i-a2/20260628T055951712859Z-e-huawei-com-cn-products-computing-ascend-atlas-300i-a2-be2af90418.md) |
| Huawei Atlas 800T A3 | 10U training supernode server | 8 Ascend 910 processors; up to 6.0 PFLOPS FP16 and 12.0 POPS INT8 | 8 x 128 GB on-chip memory; 3.2 TB/s memory bandwidth | D2D 784 GB/s bidirectional; 8 x 400GE RoCE direct and 56 x 400GE bus-protocol interfaces; up to 5 PCIe 5.0 slots | [raw](../../raw/crawler/compute-accelerators-huawei-atlas-800t-a3/20260628T060648300656Z-e-huawei-com-cn-products-computing-ascend-atlas-800t-a3-4a689659c8.md) |
| Biren Bili 106B | full-height full-length double-wide PCIe card | not captured | not captured | peak power 300 W | [raw](../../raw/crawler/compute-accelerators-biren-106b/20260628T060440806592Z-www-birentech-com-product-hardware-106b-8e22110248.md) |
| Biren Bili 106M | air-cooled OAM module | not captured | not captured | peak power 400 W | [raw](../../raw/crawler/compute-accelerators-biren-106m/20260628T060441121627Z-www-birentech-com-product-hardware-106m-bc272ef5f1.md) |
| Biren Bili 166C | full-height full-length 290 mm double-wide PCIe inference card | not captured | not captured | peak power 300 W | [raw](../../raw/crawler/compute-accelerators-biren-166c/20260628T060441390991Z-www-birentech-com-product-hardware-166c-f3c5e11442.md) |
| Biren Bili 166L | liquid-cooled OAM module | not captured | not captured | peak power 600 W | [raw](../../raw/crawler/compute-accelerators-biren-166l/20260628T060441699966Z-www-birentech-com-product-hardware-166l-93cbb57e8a.md) |
| Biren Bili 166M | 4U OAM V1.1 air-cooled module | not captured | not captured | peak power 550 W | [raw](../../raw/crawler/compute-accelerators-biren-166m/20260628T060441979925Z-www-birentech-com-product-hardware-166m-005ec7f5ac.md) |
| Cambricon MLU370-S4/S8 | half-height half-length single-slot card | 192 TOPS INT8; 96 TOPS INT16; 72 TFLOPS FP16; 72 TFLOPS BF16; 18 TFLOPS FP32 | 24 GB or 48 GB LPDDR5; 307.2 GB/s | x16 PCIe Gen4; 75 W; passive cooling | [raw](../../raw/crawler/compute-accelerators-cambricon-mlu370-s4-s8/20260628T060442871520Z-www-cambricon-com-index-php-dd51e6b9e9.md) |
| Cambricon MLU370-X4 | full-height full-length single-slot card | 256 TOPS INT8; 128 TOPS INT16; 96 TFLOPS FP16; 96 TFLOPS BF16; 24 TFLOPS FP32 | 24 GB LPDDR5; 307.2 GB/s | x16 PCIe Gen4; 150 W; passive cooling | [raw](../../raw/crawler/compute-accelerators-cambricon-mlu370-x4/20260628T060443305596Z-www-cambricon-com-index-php-56612de611.md) |
| Cambricon MLU370-X8 | full-height full-length dual-slot card | 256 TOPS INT8; 128 TOPS INT16; 96 TFLOPS FP16; 96 TFLOPS BF16; 24 TFLOPS FP32 | 48 GB LPDDR5; 614.4 GB/s | x16 PCIe Gen4; 200 GB/s bidirectional MLU-Link aggregate bandwidth; 250 W | [raw](../../raw/crawler/compute-accelerators-cambricon-mlu370-x8/20260628T060443731999Z-www-cambricon-com-index-php-da315093d5.md) |
| Enflame CloudBlazer Matrix | AI cluster product | not a single-card metric in capture | not captured | source identifies cluster positioning rather than card-level specs | [raw](../../raw/crawler/compute-accelerators-enflame-cloudblazer-matrix/20260628T060446419609Z-www-enflame-tech-com-cloudblazer-matrix-268-acb13f343e.md) |
| Enflame DeepSeek server | appliance/server | not a single-card metric in capture | not captured | source identifies system positioning rather than card-level specs | [raw](../../raw/crawler/compute-accelerators-enflame-ds-server/20260628T060446676491Z-www-enflame-tech-com-ds-server-c95070751b.md) |
| Enflame S60 | PCIe inference accelerator | not captured | not captured | PCIe 5.0 visible in capture | [raw](../../raw/crawler/compute-accelerators-enflame-s60/20260628T060446917641Z-www-enflame-tech-com-s60-7ee9e26bdb.md) |
| Iluvatar Tiangai 100 | full-length full-height dual-slot PCIe card | not captured | 32 GB HBM2; no source-visible memory bandwidth | PCIe Gen4.0 x16 lane; 250 W; source-stated 64 GB/s host bidirectional bandwidth and 64 GB/s inter-chip bandwidth. Form factor, memory, host interface, inter-chip bandwidth string, and power are resolved; host bandwidth is not normalized into a catalog field. | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-iluvatar-tg100/20260628T060648884971Z-www-iluvatar-com-productdetails-8c03246db5.md) |
| Iluvatar Tiangai 150 | training accelerator | not captured | 64 GB HBM; no source-visible memory bandwidth | board power 350 W. Form factor, host interface, compute peaks, benchmark parity, ecosystem compatibility, production-operation, training-throughput, and inference-throughput claims remain unresolved. | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-iluvatar-tg150/20260628T060649205621Z-www-iluvatar-com-productdetails-c8a0efc7a3.md) |
| Iluvatar ZK50 / ZK100 | ZK50 half-length half-height single-slot PCIe; ZK100 full-length full-height single-slot PCIe | supports FP32, FP16, INT8; exact peaks not captured and the support wording is not a resolved compute field | ZK50: 16 GB HBM2E; ZK100: 32 GB HBM2E | ZK50: 75 W; ZK100: 150 W; PCIe Gen4 x16. Form factor, memory capacity/type, host interface, and power are resolved; video/image codec capacity, CUDA ecosystem compatibility, migration-time, performance-ratio, instruction-set, cost, application-scenario, benchmark, production-operation, service-SLO, and ranking text remain boundary evidence. | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-iluvatar-zk100/20260628T060649509748Z-www-iluvatar-com-productdetails-9cf9c89ce3.md) |
| Kunlunxin R200 / R200-8F | full-height full-length dual-slot card | 256 TOPS INT8; 128 TOPS INT16; 128 TFLOPS FP16; 32 TFLOPS FP32. INT8, FP16, and FP32 are resolved; INT16 is comparison-only because the catalog has no INT16 field. | R200: 16 GB GDDR6; R200-8F: 32 GB GDDR6; 512 GB/s | PCIe Gen4 x16 compatible with Gen3/2/1; R200 150 W; R200-8F 160 W | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-kunlunxin-r200/20260628T060651804777Z-www-kunlunxin-com-product-274-html-d12bf3953a.md) |
| Kunlunxin R480-X8 | 8 OAM modules on UBB | 256 TOPS INT8 x8; 128 TOPS INT16 x8; 128 TFLOPS FP16 x8; 32 TFLOPS FP32 x8 | 32 GB x8 GDDR6; 512 GB/s x8 | 200 GB/s chip-to-chip interconnect | [raw](../../raw/crawler/compute-accelerators-kunlunxin-r480-x8/20260628T060652154506Z-www-kunlunxin-com-product-272-html-89686dc880.md) |
| Kunlunxin RG800 | full-height full-length single-slot card | 256 TOPS INT8; 128 TOPS INT16; 128 TFLOPS FP16; 32 TFLOPS FP32 | 32 GB GDDR6; 512 GB/s | PCIe 4.0 x16; 130 W | [raw](../../raw/crawler/compute-accelerators-kunlunxin-rg800/20260628T060652551492Z-www-kunlunxin-com-product-2842-html-6c65e115a3.md) |
| MetaX C500 | full-height full-length dual-slot PCIe card | not captured | 64 GB high-bandwidth memory; memory generation and bandwidth not captured | MetaXLink 2-card or 4-card interconnect; 350 W maximum power. Form factor, memory capacity, interconnect wording, and power are resolved; compute, memory type, host-interface lane count, virtualization, ecosystem, benchmark, and production-operation claims remain unresolved. | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-metax-c500/20260628T060652781059Z-www-metax-tech-com-prod-html-8de5962075.md) |
| MetaX C500X | custom-height PCIe card | not captured | 64 GB high-bandwidth memory; memory generation and bandwidth not captured | optical MetaXLink scale-up from 16 to 64 cards; 350 W maximum power. Form factor, memory capacity, interconnect wording, and power are resolved; virtualization, server/supernode, compute, memory type, benchmark, ecosystem, and production-operation claims remain unresolved. | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-metax-c500x/20260628T060653016639Z-www-metax-tech-com-prod-html-51b80e7359.md) |
| MetaX C550 | OAM 1.5 / OAM 2.0 snap-in module | not captured | 64 GB high-bandwidth memory; memory generation and bandwidth not captured | MetaXLink 8-card all-to-all up to 896GB/s; 450 W maximum power. Form factor, memory capacity, interconnect wording, and power are resolved; compute, host-interface, benchmark, server/supernode, ecosystem, and production-operation claims remain unresolved. | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-metax-c550/20260628T060653231697Z-www-metax-tech-com-prod-html-ea84ef2c6c.md) |
| MetaX C588 | OAM 2.0 snap-in module | not captured | 128 GB high-bandwidth memory; memory generation and bandwidth not captured | MetaXLink 8-card all-to-all up to 896GB/s; 850 W maximum power. Form factor, memory capacity, interconnect wording, and power are resolved; DeepSeek, compute, host-interface, benchmark, server/supernode, ecosystem, and production-operation claims remain unresolved. | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-metax-c588/20260628T060653452377Z-www-metax-tech-com-prod-html-9d84457b12.md) |
| MetaX C600 | OAM 2.0 snap-in module | not captured | large high-bandwidth memory; capacity/type/bandwidth not captured | MetaXLink and MetaXLink-E interconnect interfaces; 1000 W maximum power. Form factor, interconnect wording, and power are resolved; memory capacity/type/bandwidth, compute, ecosystem, application, server, production-operation, benchmark, topology-scale, and 128-card supernode claims remain unresolved. | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-metax-c600/20260628T060653669535Z-www-metax-tech-com-prod-html-259649e029.md) |
| NVIDIA GB300 product-family page | product overview / system family page | no single-accelerator metric captured | not captured | not captured | [raw](../../raw/crawler/compute-accelerators-nvidia-gb300/20260628T143110957451Z-www-nvidia-com-en-us-data-center-products-200b75abd8.md) |
| Moore Threads MTT S3000 | server GPU page | no parameter captured by local text extraction | no parameter captured | no parameter captured | [raw](../../raw/crawler/compute-accelerators-mthreads-s3000/20260628T060654703690Z-www-mthreads-com-product-s3000-28c8f7773e.md) |
| Moore Threads MTT S4000 | AI accelerator card page | no parameter captured by local text extraction | no parameter captured | no parameter captured | [raw](../../raw/crawler/compute-accelerators-mthreads-s4000/20260628T060655050600Z-www-mthreads-com-product-s4000-e4c4564f49.md) |
| Moore Threads MTT S5000 | training/inference GPU card page | no parameter captured by local text extraction | no parameter captured | no parameter captured | [raw](../../raw/crawler/compute-accelerators-mthreads-s5000/20260628T060655366010Z-www-mthreads-com-product-s5000-50b13e9e39.md) |
| Hygon DCU page | accelerator product page | no parameter captured by local text extraction | no parameter captured | no parameter captured | [raw](../../raw/crawler/compute-accelerators-hygon-dcu/20260628T060648544689Z-www-hygon-cn-product-accelerator-d6c4907bbd.md) |
| Dayu Paratus1 | DPU product page | no parameter captured by local text extraction | no parameter captured | no parameter captured | [raw](../../raw/crawler/compute-accelerators-dayu-paratus1/20260628T060445164573Z-www-dayudpu-com-product-paratus1-70c58cfadc.md) |
| Dayu Paratus2 | DPU product page | no parameter captured by local text extraction | no parameter captured | no parameter captured | [raw](../../raw/crawler/compute-accelerators-dayu-paratus2/20260628T060445547733Z-www-dayudpu-com-product-paratus2-24678a2fdd.md) |
| Denglin Goldwasser I/L | accelerator product page | no parameter captured by local text extraction | no parameter captured | no parameter captured | [raw](../../raw/crawler/compute-accelerators-denglin-goldwasser-i-l/20260628T060445844413Z-denglinai-com-h-col-252-html-0611810fa3.md) |
| Denglin Goldwasser II GS | accelerator product page | no clean parameter captured by local text extraction | no parameter captured | no parameter captured | [raw](../../raw/crawler/compute-accelerators-denglin-goldwasser-ii-gs/20260628T060446185315Z-denglinai-com-h-col-299-html-8fa5856573.md) |
| Vastaitech VA1 | accelerator product page | no parameter captured by local text extraction | no parameter captured | no parameter captured | [raw](../../raw/crawler/compute-accelerators-vastaitech-va1/20260628T060658419245Z-www-vastaitech-com-product-general-va1-e80df13a88.md) |
| Vastaitech VA10 | accelerator product page | no parameter captured by local text extraction | no parameter captured | no parameter captured | [raw](../../raw/crawler/compute-accelerators-vastaitech-va10/20260628T060659001491Z-www-vastaitech-com-product-general-va10-0a749592fe.md) |

# DPU, IPU, SmartNIC, And Storage-Offload Raw Comparison

| Record | Form | Network / offload parameters | Memory / host interface / power | Citation |
| --- | --- | --- | --- | --- |
| NVIDIA BlueField-3 DPU | infrastructure compute DPU | 400 Gb/s infrastructure compute platform; line-rate software-defined networking, storage, and cybersecurity | detailed SKU memory/power not captured in local page | [raw](../../raw/crawler/compute-accelerators-nvidia-bluefield-3/20260627T153315013778Z-www-nvidia-com-en-us-networking-products-data-processing-unit-d517920f8d.md) |
| NVIDIA BlueField-4 DPU | infrastructure DPU platform | 800 Gb/s infrastructure platform for gigascale AI factories; source also positions BlueField-4 around networking, data storage, and cybersecurity acceleration, but only network bandwidth is resolved | BlueField-4 STX, Vera CPU, CMX context-memory storage, storage throughput, cybersecurity/threat-detection, power, memory, host interface, compute, benchmark, production-operation, service-SLO, and ecosystem text are boundary evidence only | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-nvidia-bluefield-3/20260627T153315013778Z-www-nvidia-com-en-us-networking-products-data-processing-unit-d517920f8d.md) |
| Asterfusion CX102S-DPU | 1U open intelligent gateway with 1 or 2 DPU modules | 16 x 1GE RJ45 and 2 x 10GE SFP+; 72 Gb/s switching capacity; internal 2 x 10G links between DPU and switch chip are gateway-level evidence, not resolved DPU network_bandwidth | DPU modules use quad-core ARMv8 Cortex-A72 CPU and 8 GB DDR4 memory; only the module form factor and 8 GB DDR4 memory are resolved | [raw](../../raw/crawler/compute-accelerators-asterfusion-cx102s-dpu/20260706T204116541565Z-asterfusion-com-product-cx102s-dpu-b77dd4635a.md) |
| Asterfusion Helium DPU | PCIe DPU SmartNIC | 4 x 25GE SFP28 or 2 x 100GE QSFP28 variants; up to 100 Gb/s mixed-service processing is resolved as source-stated network processing capability; NFV comparison lists 60G processing as boundary evidence | PCIe x8 Gen3.0/4.0; 24-core ARM processor; memory expandable to 64 GB; NFV comparison row lists 60 W card power | [raw](../../raw/crawler/compute-accelerators-asterfusion-helium-dpu/20260706T204116820726Z-asterfusion-com-product-helium-dpu-121181ec67.md) |
| Corigine Agilio CX 2x25GbE SmartNIC | SmartNIC | 2 x 25GbE ports; SFP+ 10GbE / SFP28 25GbE | 2 GB DDR3 onboard memory; PCIe Base 3.0 compatible with 1.1/2.0 | [raw](../../raw/crawler/compute-accelerators-corigine-agilio-cx-pdf/20260628T060444859456Z-storage-corigine-com-cn-uploadfiles-pdf-2022-01-24-1-agilio-20cx-202x25gbe-20smartnic-20-e-a138a8aa07.md) |
| JaguarMicro Yunxiao DPU | DPU product | 2 x 25G Ethernet is resolved as aggregate 50 Gb/s network bandwidth; RoCE v1/v2, iWARP, NVMe-oF, VLAN, VXLAN, GRE, Geneve, L2VPN, virtio-net/virtio-blk, elastic network/storage, security isolation, QoS, hot-plug, live migration, and hot-upgrade text remains boundary evidence | detailed memory, host interface, and power not captured | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-jaguarmicro-yunxiao-dpu/20260628T060651455844Z-www-jaguarmicro-com-n4-html-87a5670154.md) |
| Resnics Stargate-N1025 | half-height half-length single-wide PCIe DPU SmartNIC | 2 x SFP28 25G Ethernet and 1000BASE-T management port; P4 programmable vSwitch acceleration | quad-core Cortex-A53; 8 GB DDR4 SDRAM x72; PCIe Gen3 x8; 25 W typical | [raw](../../raw/crawler/compute-accelerators-resnics-stargate-n1025/20260628T060657022930Z-www-resnics-com-product-stargate-n1025-dpu-8584bb028f.md) |
| Resnics Stargate-N2025 | full-height double-wide 3/4-length PCIe DPU | 2 x SFP28 25G Ethernet; SR-IOV 32 PF and 2K VF, RDMA queue pair 256, P4 flow-table/session/protocol/storage-offload, line-rate, low-latency, benchmark, and production-operation values are comparison-only boundary evidence | 6-core Intel Icelake-D eCPU; 8 GB DDR4 FPGA memory and 16 GB DDR4 SoC memory; PCIe Gen4 x8; 150 W | [raw](../../raw/crawler/compute-accelerators-resnics-stargate-n2025/20260628T060657411423Z-www-resnics-com-product-stargate-n2025-dpu-f2feeec038.md) |
| Resnics Stargate-S1100 | NVMe-oF storage accelerator | 2 x QSFP28 100G Ethernet; 4K block, 4 SSD: read 2.7M IOPS and write 2M IOPS; added latency read <10 us, write <20 us | PCIe Gen3 x16; 16 GB DDR4 FPGA memory and 16 GB DDR4 ARM CPU memory; 35 W | [raw](../../raw/crawler/compute-accelerators-resnics-stargate-s1100/20260628T060657808728Z-www-resnics-com-product-stargate-s1100-nvme-of-e3a4fe3da7.md) |
| Yusur K2-Pro | DPU chip / DPU product family | 16 clusters / 128 NP cores; DOE lookup 600M/s; NoC 3 Tbps / 1500 Mpps; LAN 200 Gb/s line-rate switching; NVMe-oF engine; 2M IOPS | product series lists 2 x 100/40/25/10GbE ports and 2 x PCIe Gen3 x16; DOE/NoC/packet-rate/NVMe-oF/unspecified IOPS values are comparison-only unless a schema field and read/write boundary are added | [raw](../../raw/crawler/compute-accelerators-yusur-k2-pro/20260628T060700357328Z-www-yusur-tech-dpu-k2-pro-c4119da6b0.md) |
| Yusur SWIFT-2200N Pro | low-latency network DPU card | PCIe one-way pass-through latency <230 ns; 1/2 RTT loopback latency 1 us; network jitter <20 ns | interface, memory, and power not captured in local page; latency and jitter remain comparison-only because the catalog lacks general network-latency and jitter fields | [raw](../../raw/crawler/compute-accelerators-yusur-swift-2200n/20260628T060700719790Z-www-yusur-tech-product-swift-swift2200n-7afeac0475.md) |
| Nebula DPU200 / RNIC IP / SNIC S1400 | DPU/RNIC/SmartNIC pages | no parameter captured by local text extraction | no parameter captured | [DPU200](../../raw/crawler/compute-accelerators-nebula-dpu200/20260628T060655740838Z-www-nebula-matrix-com-dpu200-7e44cc4782.md), [RNIC IP](../../raw/crawler/compute-accelerators-nebula-rnic-ip/20260628T060656128184Z-www-nebula-matrix-com-rnic-ip-6a2d630a55.md), [SNIC S1400](../../raw/crawler/compute-accelerators-nebula-snic-s1400/20260628T060656459873Z-www-nebula-matrix-com-snic-s1400-3a683422fd.md) |

# Synthesis

In the current evidence, NVIDIA H200 SXM is the clearest high-end single GPU
record: it combines 141 GB HBM3e, 4.8 TB/s memory bandwidth, resolved FP64,
FP32, BF16, FP16, and FP8 peaks, NVLink plus PCIe Gen5 interconnect evidence,
and an up to 700 W configurable TDP. H200 NVL and benchmark text remain useful
comparison boundaries, not fields in the H200 SXM resolved row. Huawei Atlas
300I A2, Cambricon MLU370, and Kunlunxin R200/R200-8F/RG800 expose more modest
card-level performance and memory, with power envelopes from 75 W to 350 W
depending on form factor. The structured catalog now resolves Huawei Atlas
300I A2 as separate 32 GB and 64 GB variants with shared INT8/FP16, form-factor,
PCIe 5.0, and power fields plus per-variant memory capacity and bandwidth. It
also resolves Kunlunxin
R200/R200-8F INT8, FP16, FP32, GDDR6 memory, per-variant memory capacity, memory
bandwidth, PCIe host-interface, form-factor, and power fields from the local
product page; source-visible INT16 remains a raw comparison value rather than a
resolved catalog field.

The highest aggregate numbers are cloud/system records, not single cards. AWS
Trn2 and Huawei Atlas 800T A3 report multi-chip or multi-server totals, while
Kunlunxin R480-X8 reports an 8-module aggregate. These are useful capacity
planning records, but must be normalized before card-to-card comparison.

Several domestic GPU/AI accelerator vendors expose form factor and power more
clearly than compute peaks in the captured HTML. Biren pages remain useful for
deployment envelope comparison only. MetaX C500, C500X, C550, and C588 now have
structured deployment-envelope rows for form factor, memory capacity,
MetaXLink interconnect wording, and maximum power; MetaX C600 adds only OAM 2.0
form factor, MetaXLink/MetaXLink-E interconnect wording, and 1000 W maximum
power. The structured catalog should add compute, memory capacity for C600,
memory generation, memory bandwidth, host-interface, and benchmark observations
only if future official tables expose those fields.

DPU and SmartNIC records have a separate comparison axis. NVIDIA BlueField-3,
NVIDIA BlueField-4, Yusur K2-Pro, Yusur SWIFT-2200N Pro, Asterfusion Helium,
Resnics Stargate, and Corigine Agilio are infrastructure accelerators where network bandwidth,
programmable packet processing, storage offload, IOPS, and latency matter more
than tensor FLOPS.
R10 task 3 promotes a bounded Resnics slice into structured facts:
Stargate-N1025 resolves form factor, source-stated aggregate data-port
bandwidth, memory, host interface, and typical power, while Stargate-S1100
resolves host interface, power, 4K/4-SSD read and write IOPS, and added-latency
upper bounds. The 2026-07-08 continuation adds Corigine Agilio CX 2x25GbE as a
structured SmartNIC row for official product-brief form factor, 50 Gb/s
aggregate port bandwidth, 2 GB DDR3 memory, and PCIe x8 host-interface wording.
Continuation parent 3 adds Yusur K2-Pro form factor, 200 Gb/s source-stated
network bandwidth, and `2 x PCIe Gen3 x16` host interface, plus the
SWIFT-2200N Pro low-latency DPU-card form factor. K2-Pro DOE lookup, NoC
throughput, packet rate, NVMe-oF engine, unspecified 2M IOPS, and SWIFT latency
or jitter values stay in the raw comparison table until a schema field and
exact metric boundary support promotion. Continuation parent 7 adds Resnics
Stargate-N2025 form factor, aggregate 50 Gb/s data-port bandwidth,
split-pool DDR4 memory capacity, `PCIe Gen4 x8`, and 150 W power as a
product-spec catalog slice. It does not promote N2025 SR-IOV counts, RDMA
queue-pair count, P4 table/session/protocol/storage-offload details,
line-rate or low-latency wording, benchmarks, or production-operation claims.
Continuation parent 9 adds Asterfusion Helium DPU SmartNIC resolved fields for
PCIe DPU SmartNIC form factor, source-stated 100 Gb/s mixed-service processing
capability, expandable 64 GB memory, `PCIe x8 Gen3.0/4.0`, and 60 W source
comparison power, plus a CX102S-DPU module row for 8 GB DDR4 memory inside a 1U
gateway. CX102S 72 Gb/s switching capacity, gateway port layout, one- or
two-DPU system variants, Helium physical port variant aggregation, NFV latency,
session-count, offload, storage-acceleration, and cost-reduction claims remain
raw comparison or boundary evidence. Continuation parent 15 adds JaguarMicro
Yunxiao DPU as a structured product row for aggregate 50 Gb/s Ethernet
bandwidth from the local 2 x 25G announcement text. Its RoCE/iWARP/NVMe-oF and
tunnel protocol list, virtio acceleration, elastic storage/network, security,
QoS, hot-migration, hot-upgrade, memory, host-interface, power, benchmark, and
production-operation text remains boundary evidence rather than resolved
catalog, protocol-level storage-fabric, benchmark, operations, or SLO proof.
Continuation parent 18 adds NVIDIA BlueField-4 DPU as the next bounded
BlueField row with only 800 Gb/s network bandwidth resolved from the local
platform capture. The same capture's STX, CMX/context-memory storage,
cybersecurity, threat-detection, validated-design, ecosystem, benchmark,
production-operation, and service-SLO wording remains comparison or boundary
evidence rather than resolved catalog or storage-fabric proof.
Remaining DPU/SmartNIC rows likewise stay raw-only until a future task promotes
their exact product or variant boundaries.

# Citations

- ../../data/compute_accelerators/skus/sample-skus.yaml
- ../../data/compute_accelerators/observations/sample-observations.yaml
- ../../data/compute_accelerators/resolved/sample-resolved-specs.yaml
- ../../raw/crawler/compute-accelerators-nvidia-h200/20260627T153310569545Z-www-nvidia-com-en-us-data-center-h200-7d05aa2873.md
- ../../raw/crawler/compute-accelerators-nvidia-h200/20260705T041039962650Z-www-nvidia-com-en-us-data-center-h200-a464325a64.md
- ../../manifest-ai-infra-expansion-continuation-20260708-parent-4-gap-proof.json
- ../../raw/crawler/compute-accelerators-asterfusion-helium-dpu/20260706T204116820726Z-asterfusion-com-product-helium-dpu-121181ec67.md
- ../../raw/crawler/compute-accelerators-asterfusion-cx102s-dpu/20260706T204116541565Z-asterfusion-com-product-cx102s-dpu-b77dd4635a.md
- ../../manifest-ai-infra-expansion-continuation-20260708-parent-9-gap-proof.json
- ../../manifest-ai-infra-expansion-continuation-20260708-parent-10-gap-proof.json
- ../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-rel-2-19-3-html.md
- ../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-rel-2-18-3-html.md
- ../../raw/github/nvidia-nccl-closed-issues/api-pages/closed-issues-page-011.json.gz
- ../../raw/github/sgl-project-sglang-closed-issues-prs/comment-pages/issue-comments-page-205.json.gz
- ../../raw/crawler/compute-accelerators-aws-trn2/20260627T153315637188Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md
- ../../raw/crawler/compute-accelerators-huawei-atlas-300i-a2/20260628T055951712859Z-e-huawei-com-cn-products-computing-ascend-atlas-300i-a2-be2af90418.md
- ../../manifest-ai-infra-expansion-continuation-20260708-parent-14-gap-proof.json
- ../../raw/crawler/compute-accelerators-huawei-atlas-800t-a3/20260628T060648300656Z-e-huawei-com-cn-products-computing-ascend-atlas-800t-a3-4a689659c8.md
- ../../raw/crawler/compute-accelerators-cambricon-mlu370-s4-s8/20260628T060442871520Z-www-cambricon-com-index-php-dd51e6b9e9.md
- ../../raw/crawler/compute-accelerators-cambricon-mlu370-x4/20260628T060443305596Z-www-cambricon-com-index-php-56612de611.md
- ../../raw/crawler/compute-accelerators-cambricon-mlu370-x8/20260628T060443731999Z-www-cambricon-com-index-php-da315093d5.md
- ../../raw/crawler/compute-accelerators-kunlunxin-r200/20260628T060651804777Z-www-kunlunxin-com-product-274-html-d12bf3953a.md
- ../../raw/crawler/compute-accelerators-kunlunxin-r480-x8/20260628T060652154506Z-www-kunlunxin-com-product-272-html-89686dc880.md
- ../../raw/crawler/compute-accelerators-kunlunxin-rg800/20260628T060652551492Z-www-kunlunxin-com-product-2842-html-6c65e115a3.md
- ../../raw/crawler/compute-accelerators-nvidia-bluefield-3/20260627T153315013778Z-www-nvidia-com-en-us-networking-products-data-processing-unit-d517920f8d.md
- ../../manifest-ai-infra-expansion-continuation-20260708-parent-18-gap-proof.json
- ../../manifest-ai-infra-expansion-2026-07-07-r9-task-2-gap-proof.json
- ../../manifest-ai-infra-expansion-2026-07-07-r10-task-2-gap-proof.json
- ../../manifest-ai-infra-expansion-2026-07-07-r10-task-3-gap-proof.json
- ../../manifest-ai-infra-expansion-continuation-20260708-parent-1-gap-proof.json
- ../../manifest-ai-infra-expansion-continuation-20260708-parent-3-gap-proof.json
- ../../manifest-ai-infra-expansion-continuation-20260708-parent-7-gap-proof.json
- ../../manifest-ai-infra-expansion-continuation-20260708-parent-9-gap-proof.json
- ../../manifest-ai-infra-expansion-continuation-20260708-parent-10-gap-proof.json
- ../../raw/crawler/compute-accelerators-iluvatar-tg100/20260628T060648884971Z-www-iluvatar-com-productdetails-8c03246db5.md
- ../../raw/crawler/compute-accelerators-iluvatar-tg150/20260628T060649205621Z-www-iluvatar-com-productdetails-c8a0efc7a3.md
- ../../manifest-ai-infra-expansion-continuation-20260708-parent-11-gap-proof.json
- ../../raw/crawler/compute-accelerators-metax-c500/20260628T060652781059Z-www-metax-tech-com-prod-html-8de5962075.md
- ../../raw/crawler/compute-accelerators-metax-c500x/20260628T060653016639Z-www-metax-tech-com-prod-html-51b80e7359.md
- ../../raw/crawler/compute-accelerators-metax-c550/20260628T060653231697Z-www-metax-tech-com-prod-html-ea84ef2c6c.md
- ../../raw/crawler/compute-accelerators-metax-c588/20260628T060653452377Z-www-metax-tech-com-prod-html-9d84457b12.md
- ../../manifest-ai-infra-expansion-continuation-20260708-parent-12-gap-proof.json
- ../../raw/crawler/compute-accelerators-jaguarmicro-yunxiao-dpu/20260628T060651455844Z-www-jaguarmicro-com-n4-html-87a5670154.md
- ../../manifest-ai-infra-expansion-continuation-20260708-parent-15-gap-proof.json
