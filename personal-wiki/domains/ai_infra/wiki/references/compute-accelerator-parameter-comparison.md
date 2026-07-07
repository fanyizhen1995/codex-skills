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
  - ../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-rel-2-19-3-html.md
  - ../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-rel-2-18-3-html.md
  - ../../raw/github/nvidia-nccl-closed-issues/api-pages/closed-issues-page-011.json.gz
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/comment-pages/issue-comments-page-205.json.gz
  - ../../raw/crawler/compute-accelerators-aws-trn2/20260627T153315637188Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md
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
  - ../../raw/crawler/compute-accelerators-enflame-s60/20260706T204121967738Z-www-enflame-tech-com-7d7fdd552a.md
  - ../../manifest-ai-infra-expansion-2026-07-07-r9-task-2-gap-proof.json
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
| Corigine Agilio CX PDF and Asterfusion DPU captures | Exact content-hash refreshes for existing SmartNIC/DPU rows; cite as tracked July evidence without adding new normalized fields. [Corigine](../../raw/crawler/compute-accelerators-corigine-agilio-cx-pdf/20260706T204120429357Z-storage-corigine-com-cn-uploadfiles-pdf-2022-01-24-1-agilio-20cx-202x25gbe-20smartnic-20-e-a138a8aa07.md), [Asterfusion Helium](../../raw/crawler/compute-accelerators-asterfusion-helium-dpu/20260706T204116820726Z-asterfusion-com-product-helium-dpu-121181ec67.md) |
| Enflame S60 July capture | Intentionally not used to replace the older S60-specific citation because the July capture resolves to the Enflame homepage and does not expose the old PCIe 5.0 field in local text. [July homepage capture](../../raw/crawler/compute-accelerators-enflame-s60/20260706T204121967738Z-www-enflame-tech-com-7d7fdd552a.md) |

# Quick Read

- Highest single-accelerator memory captured in the structured catalog:
  AMD Instinct MI325X at 256 GB, followed by NVIDIA H200 SXM at 141 GB and
  Intel Gaudi 3 HL-338 at 128 GB. R9 task 2 adds source-backed structured
  rows for Cambricon MLU370-X4, Cambricon MLU370-X8, and Kunlunxin RG800,
  including compute, memory, host-interface, form-factor, and power fields.
  [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml)
- Clearest high-end single-GPU raw record: NVIDIA H200 SXM/H200 NVL. It is the
  only captured single-GPU row with complete high-end tensor, memory bandwidth,
  NVLink, PCIe, and power fields. [raw](../../raw/crawler/compute-accelerators-nvidia-h200/20260627T153310569545Z-www-nvidia-com-en-us-data-center-h200-7d05aa2873.md)
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
- Strong domestic card-level comparison set: Huawei Atlas 300I A2, Cambricon
  MLU370, and Kunlunxin R200/RG800 all expose enough local raw parameters to
  compare compute, memory, host interface, and power as individual cards.
  [Atlas 300I A2](../../raw/crawler/compute-accelerators-huawei-atlas-300i-a2/20260628T055951712859Z-e-huawei-com-cn-products-computing-ascend-atlas-300i-a2-be2af90418.md),
  [MLU370-S4/S8](../../raw/crawler/compute-accelerators-cambricon-mlu370-s4-s8/20260628T060442871520Z-www-cambricon-com-index-php-dd51e6b9e9.md),
  [MLU370-X4](../../raw/crawler/compute-accelerators-cambricon-mlu370-x4/20260628T060443305596Z-www-cambricon-com-index-php-56612de611.md),
  [MLU370-X8](../../raw/crawler/compute-accelerators-cambricon-mlu370-x8/20260628T060443731999Z-www-cambricon-com-index-php-da315093d5.md),
  [R200](../../raw/crawler/compute-accelerators-kunlunxin-r200/20260628T060651804777Z-www-kunlunxin-com-product-274-html-d12bf3953a.md),
  [RG800](../../raw/crawler/compute-accelerators-kunlunxin-rg800/20260628T060652551492Z-www-kunlunxin-com-product-2842-html-6c65e115a3.md)
- Aggregate records must be normalized before card-to-card comparison: AWS
  Trn2/UltraServer, Huawei Atlas 800T A3, and Kunlunxin R480-X8 report
  multi-chip or system-level totals. Use them for capacity planning, not as
  direct single-card substitutes. [AWS Trn2](../../raw/crawler/compute-accelerators-aws-trn2/20260627T153315637188Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md),
  [Atlas 800T A3](../../raw/crawler/compute-accelerators-huawei-atlas-800t-a3/20260628T060648300656Z-e-huawei-com-cn-products-computing-ascend-atlas-800t-a3-4a689659c8.md),
  [R480-X8](../../raw/crawler/compute-accelerators-kunlunxin-r480-x8/20260628T060652154506Z-www-kunlunxin-com-product-272-html-89686dc880.md)
- DPU/SmartNIC records are not FLOPS peers. NVIDIA BlueField-3, Asterfusion
  Helium, Resnics Stargate, Yusur K2-Pro, and Corigine Agilio are better
  compared by line rate, packet/storage offload, PCIe generation, memory, IOPS,
  and latency. [BlueField-3](../../raw/crawler/compute-accelerators-nvidia-bluefield-3/20260627T153315013778Z-www-nvidia-com-en-us-networking-products-data-processing-unit-d517920f8d.md),
  [Asterfusion Helium](../../raw/crawler/compute-accelerators-asterfusion-helium-dpu/20260628T060438266386Z-asterfusion-com-product-helium-dpu-121181ec67.md),
  [Resnics Stargate-S1100](../../raw/crawler/compute-accelerators-resnics-stargate-s1100/20260628T060657808728Z-www-resnics-com-product-stargate-s1100-nvme-of-e3a4fe3da7.md),
  [Yusur K2-Pro](../../raw/crawler/compute-accelerators-yusur-k2-pro/20260628T060700357328Z-www-yusur-tech-dpu-k2-pro-c4119da6b0.md),
  [Corigine Agilio CX](../../raw/crawler/compute-accelerators-corigine-agilio-cx-pdf/20260628T060444859456Z-storage-corigine-com-cn-uploadfiles-pdf-2022-01-24-1-agilio-20cx-202x25gbe-20smartnic-20-e-a138a8aa07.md)

# Resolved Catalog Fields

| Record | Type | Resolved parameters | Citation |
| --- | --- | --- | --- |
| NVIDIA H200 SXM | GPU module | 141 GB memory; 4.8 TB/s memory bandwidth | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml) |
| AMD Instinct MI325X | GPU module | 256 GB memory | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml) |
| Intel Gaudi 3 HL-338 | AI ASIC / PCIe card | 128 GB memory | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml) |
| NXP i.MX 95 eIQ Neutron NPU | integrated SoC NPU | integrated SoC NPU form factor | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml) |
| NVIDIA BlueField-3 DPU | DPU | 400 Gb/s network bandwidth | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml) |
| AWS Trainium2 Trn2 offering | cloud AI ASIC offering | 16 accelerators per `trn2.48xlarge` / `trn2u.48xlarge` offering | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml) |
| Google Cloud TPU v5p offering | cloud TPU offering | cloud offering form factor | [observations](../../data/compute_accelerators/observations/sample-observations.yaml) |
| AMD Alveo V80 | FPGA / PCIe card | no resolved parameter yet | [SKUs](../../data/compute_accelerators/skus/sample-skus.yaml) |
| Intel IPU Adapter E2100 | IPU / PCIe card | 200 Gb/s network bandwidth | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml) |
| Microsoft Maia 200 | cloud-integrated DSA | 216 GB memory; 7 TB/s memory bandwidth | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml) |
| Cambricon MLU370-X4 | AI ASIC / PCIe card | 256 TOPS INT8; 96 TFLOPS FP16; 96 TFLOPS BF16; 24 TFLOPS FP32; 24 GB LPDDR5; 307.2 GB/s memory bandwidth; x16 PCIe Gen4; 150 W; full-height full-length single-slot card | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-cambricon-mlu370-x4/20260628T060443305596Z-www-cambricon-com-index-php-56612de611.md) |
| Cambricon MLU370-X8 | AI ASIC / PCIe card | 256 TOPS INT8; 96 TFLOPS FP16; 96 TFLOPS BF16; 24 TFLOPS FP32; 48 GB LPDDR5; 614.4 GB/s memory bandwidth; x16 PCIe Gen4; MLU-Link 200 GB/s bidirectional aggregate; 250 W; full-height full-length dual-slot card | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-cambricon-mlu370-x8/20260628T060443731999Z-www-cambricon-com-index-php-da315093d5.md) |
| Kunlunxin RG800 | AI ASIC / PCIe card | 256 TOPS INT8; 128 TFLOPS FP16; 32 TFLOPS FP32; 32 GB GDDR6; 512 GB/s memory bandwidth; PCIe 4.0 x16; 130 W; full-height full-length single-slot card | [resolved specs](../../data/compute_accelerators/resolved/sample-resolved-specs.yaml), [raw](../../raw/crawler/compute-accelerators-kunlunxin-rg800/20260628T060652551492Z-www-kunlunxin-com-product-2842-html-6c65e115a3.md) |

# Unresolved Runtime Evidence

| Record | Evidence status | Locally supported facts | Not locally resolved | Citation |
| --- | --- | --- | --- | --- |
| NVIDIA H800 | Runtime and release-note evidence only; no product-spec or resolved catalog row captured | Hopper-class GPU grouping in NCCL release notes; observed as `H800 SXM5` / `NVIDIA H800` in an NCCL issue log; one SGLang issue comment reports 8 x NVIDIA H800 with CUDA compute capability 9.0 and NV18 intra-node GPU topology | Memory capacity, memory bandwidth, tensor/INT8/FP64/FP32 performance, power, host interface, and official NVLink bandwidth | [NCCL 2.19.3](../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-rel-2-19-3-html.md), [NCCL 2.18.3](../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-rel-2-18-3-html.md), [NCCL issue API page](../../raw/github/nvidia-nccl-closed-issues/api-pages/closed-issues-page-011.json.gz), [SGLang issue comment API page](../../raw/github/sgl-project-sglang-closed-issues-prs/comment-pages/issue-comments-page-205.json.gz) |

# AI Accelerator And System Raw Comparison

| Record | Form | Compute | Memory and bandwidth | Power / interface / interconnect | Citation |
| --- | --- | --- | --- | --- | --- |
| NVIDIA H200 SXM / H200 NVL | SXM module / PCIe dual-slot air-cooled | H200 SXM: FP64 34 TFLOPS, FP32 67 TFLOPS, TF32 989 TFLOPS, BF16/FP16 1,979 TFLOPS, FP8/INT8 3,958 TFLOPS; H200 NVL: FP64 30 TFLOPS, FP32 60 TFLOPS, BF16/FP16 1,671 TFLOPS, FP8/INT8 3,341 TFLOPS | 141 GB; 4.8 TB/s | SXM up to 700 W; NVL up to 600 W; NVLink 900 GB/s; PCIe Gen5 128 GB/s | [raw](../../raw/crawler/compute-accelerators-nvidia-h200/20260627T153310569545Z-www-nvidia-com-en-us-data-center-h200-7d05aa2873.md) |
| AWS Trainium2 Trn2 / Trn2 UltraServer | cloud offering | Trn2 instance: up to 20.8 FP8 PFLOPS; UltraServer: up to 83.2 FP8 PFLOPS | Trn2: 1.5 TB HBM3 and 46 TBps total memory bandwidth; UltraServer: 6 TB HBM and 185 TBps total bandwidth | Trn2: 16 Trainium2 chips and 3.2 Tbps EFAv3; UltraServer: 64 chips and 12.8 Tbps EFAv3 | [raw](../../raw/crawler/compute-accelerators-aws-trn2/20260627T153315637188Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md) |
| Huawei Atlas 300I A2 | dual-slot full-height full-length PCIe inference card | 560 TOPS INT8; 280 TFLOPS FP16; 8-core 2.0 GHz CPU | 32 GB at 0.8 TB/s or 64 GB at 1.6 TB/s on-card memory | PCIe 5.0; maximum 350 W; passive air cooling | [raw](../../raw/crawler/compute-accelerators-huawei-atlas-300i-a2/20260628T055951712859Z-e-huawei-com-cn-products-computing-ascend-atlas-300i-a2-be2af90418.md) |
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
| Iluvatar Tiangai 100 | full-length full-height dual-slot PCIe card | not captured | 32 GB HBM2 | PCIe Gen4 x16; 250 W; 64 GB/s host bidirectional bandwidth and 64 GB/s inter-chip bandwidth | [raw](../../raw/crawler/compute-accelerators-iluvatar-tg100/20260628T060648884971Z-www-iluvatar-com-productdetails-8c03246db5.md) |
| Iluvatar Tiangai 150 | training accelerator | not captured | 64 GB HBM | board power 350 W | [raw](../../raw/crawler/compute-accelerators-iluvatar-tg150/20260628T060649205621Z-www-iluvatar-com-productdetails-c8a0efc7a3.md) |
| Iluvatar ZK50 / ZK100 | ZK50 half-length half-height single-slot PCIe; ZK100 full-length full-height single-slot PCIe | supports FP32, FP16, INT8; exact peaks not captured | ZK50: 16 GB HBM2E; ZK100: 32 GB HBM2E | ZK50: 75 W; ZK100: 150 W; PCIe Gen4 x16 | [raw](../../raw/crawler/compute-accelerators-iluvatar-zk100/20260628T060649509748Z-www-iluvatar-com-productdetails-9cf9c89ce3.md) |
| Kunlunxin R200 / R200-8F | full-height full-length dual-slot card | 256 TOPS INT8; 128 TOPS INT16; 128 TFLOPS FP16; 32 TFLOPS FP32 | R200: 16 GB GDDR6; R200-8F: 32 GB GDDR6; 512 GB/s | PCIe Gen4 x16 compatible with Gen3/2/1; R200 150 W; R200-8F 160 W | [raw](../../raw/crawler/compute-accelerators-kunlunxin-r200/20260628T060651804777Z-www-kunlunxin-com-product-274-html-d12bf3953a.md) |
| Kunlunxin R480-X8 | 8 OAM modules on UBB | 256 TOPS INT8 x8; 128 TOPS INT16 x8; 128 TFLOPS FP16 x8; 32 TFLOPS FP32 x8 | 32 GB x8 GDDR6; 512 GB/s x8 | 200 GB/s chip-to-chip interconnect | [raw](../../raw/crawler/compute-accelerators-kunlunxin-r480-x8/20260628T060652154506Z-www-kunlunxin-com-product-272-html-89686dc880.md) |
| Kunlunxin RG800 | full-height full-length single-slot card | 256 TOPS INT8; 128 TOPS INT16; 128 TFLOPS FP16; 32 TFLOPS FP32 | 32 GB GDDR6; 512 GB/s | PCIe 4.0 x16; 130 W | [raw](../../raw/crawler/compute-accelerators-kunlunxin-rg800/20260628T060652551492Z-www-kunlunxin-com-product-2842-html-6c65e115a3.md) |
| MetaX C500 | full-height full-length dual-slot PCIe card | not captured | 64 GB high-bandwidth memory | MetaXLink 2-card or 4-card interconnect; 350 W | [raw](../../raw/crawler/compute-accelerators-metax-c500/20260628T060652781059Z-www-metax-tech-com-prod-html-8de5962075.md) |
| MetaX C500X | custom-height PCIe card | not captured | 64 GB high-bandwidth memory | optical MetaXLink scale-up from 16 to 64 cards; 350 W | [raw](../../raw/crawler/compute-accelerators-metax-c500x/20260628T060653016639Z-www-metax-tech-com-prod-html-51b80e7359.md) |
| MetaX C550 | OAM 1.5 / OAM 2.0 module | not captured | 64 GB high-bandwidth memory | MetaXLink 8-card all-to-all up to 896 GB/s; 450 W | [raw](../../raw/crawler/compute-accelerators-metax-c550/20260628T060653231697Z-www-metax-tech-com-prod-html-ea84ef2c6c.md) |
| MetaX C588 | OAM 2.0 module | not captured | 128 GB high-bandwidth memory | MetaXLink 8-card all-to-all up to 896 GB/s; 850 W | [raw](../../raw/crawler/compute-accelerators-metax-c588/20260628T060653452377Z-www-metax-tech-com-prod-html-9d84457b12.md) |
| MetaX C600 | OAM 2.0 module | not captured | large high-bandwidth memory; capacity not captured | MetaXLink and MetaXLink-E; up to 128-card supernode; 1,000 W | [raw](../../raw/crawler/compute-accelerators-metax-c600/20260628T060653669535Z-www-metax-tech-com-prod-html-259649e029.md) |
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
| Asterfusion CX102S-DPU | 1U open intelligent gateway with 1 or 2 DPU modules | 16 x 1GE RJ45 and 2 x 10GE SFP+; 72 Gb/s switching capacity; internal 2 x 10G links between DPU and switch chip | DPU modules use quad-core ARMv8 Cortex-A72 CPU and 8 GB DDR4 memory | [raw](../../raw/crawler/compute-accelerators-asterfusion-cx102s-dpu/20260628T060437955885Z-asterfusion-com-product-cx102s-dpu-b77dd4635a.md) |
| Asterfusion Helium DPU | PCIe DPU SmartNIC | 4 x 25GE SFP28 or 2 x 100GE QSFP28; up to 100 Gb/s mixed-service processing; NFV comparison lists 60G processing | PCIe x8 Gen3/4; 24-core ARM processor; memory expandable to 64 GB; comparison row lists 60 W card power | [raw](../../raw/crawler/compute-accelerators-asterfusion-helium-dpu/20260628T060438266386Z-asterfusion-com-product-helium-dpu-121181ec67.md) |
| Corigine Agilio CX 2x25GbE SmartNIC | SmartNIC | 2 x 25GbE ports; SFP+ 10GbE / SFP28 25GbE | 2 GB DDR3 onboard memory; PCIe Base 3.0 compatible with 1.1/2.0 | [raw](../../raw/crawler/compute-accelerators-corigine-agilio-cx-pdf/20260628T060444859456Z-storage-corigine-com-cn-uploadfiles-pdf-2022-01-24-1-agilio-20cx-202x25gbe-20smartnic-20-e-a138a8aa07.md) |
| JaguarMicro Yunxiao DPU | DPU product | 2 x 25G Ethernet; supports RoCE v1/v2, iWARP, NVMe-oF, VLAN, VXLAN, GRE, Geneve, and L2VPN | detailed memory/power not captured | [raw](../../raw/crawler/compute-accelerators-jaguarmicro-yunxiao-dpu/20260628T060651455844Z-www-jaguarmicro-com-n4-html-87a5670154.md) |
| Resnics Stargate-N1025 | half-height half-length single-wide PCIe DPU SmartNIC | 2 x SFP28 25G Ethernet and 1000BASE-T management port; P4 programmable vSwitch acceleration | quad-core Cortex-A53; 8 GB DDR4 SDRAM x72; PCIe Gen3 x8; 25 W typical | [raw](../../raw/crawler/compute-accelerators-resnics-stargate-n1025/20260628T060657022930Z-www-resnics-com-product-stargate-n1025-dpu-8584bb028f.md) |
| Resnics Stargate-N2025 | full-height double-wide 3/4-length PCIe DPU | 2 x SFP28 25G Ethernet; SR-IOV 32 PF and 2K VF; RDMA queue pair 256 | 6-core Intel Icelake-D eCPU; 8 GB DDR4 FPGA memory and 16 GB DDR4 SoC memory; PCIe Gen4 x8; 150 W | [raw](../../raw/crawler/compute-accelerators-resnics-stargate-n2025/20260628T060657411423Z-www-resnics-com-product-stargate-n2025-dpu-f2feeec038.md) |
| Resnics Stargate-S1100 | NVMe-oF storage accelerator | 2 x QSFP28 100G Ethernet; 4K block, 4 SSD: read 2.7M IOPS and write 2M IOPS; added latency read <10 us, write <20 us | PCIe Gen3 x16; 16 GB DDR4 FPGA memory and 16 GB DDR4 ARM CPU memory; 35 W | [raw](../../raw/crawler/compute-accelerators-resnics-stargate-s1100/20260628T060657808728Z-www-resnics-com-product-stargate-s1100-nvme-of-e3a4fe3da7.md) |
| Yusur K2-Pro | DPU chip / DPU product family | 16 clusters / 128 NP cores; DOE lookup 600M/s; NoC 3 Tbps / 1500 Mpps; LAN 200 Gb/s line-rate switching; NVMe-oF engine; 2M IOPS | product series lists 2 x 100/40/25/10GbE ports and 2 x PCIe Gen3 x16 | [raw](../../raw/crawler/compute-accelerators-yusur-k2-pro/20260628T060700357328Z-www-yusur-tech-dpu-k2-pro-c4119da6b0.md) |
| Yusur SWIFT-2200N Pro | low-latency network DPU card | PCIe one-way pass-through latency <230 ns; 1/2 RTT loopback latency 1 us; network jitter <20 ns | interface, memory, and power not captured in local page | [raw](../../raw/crawler/compute-accelerators-yusur-swift-2200n/20260628T060700719790Z-www-yusur-tech-product-swift-swift2200n-7afeac0475.md) |
| Nebula DPU200 / RNIC IP / SNIC S1400 | DPU/RNIC/SmartNIC pages | no parameter captured by local text extraction | no parameter captured | [DPU200](../../raw/crawler/compute-accelerators-nebula-dpu200/20260628T060655740838Z-www-nebula-matrix-com-dpu200-7e44cc4782.md), [RNIC IP](../../raw/crawler/compute-accelerators-nebula-rnic-ip/20260628T060656128184Z-www-nebula-matrix-com-rnic-ip-6a2d630a55.md), [SNIC S1400](../../raw/crawler/compute-accelerators-nebula-snic-s1400/20260628T060656459873Z-www-nebula-matrix-com-snic-s1400-3a683422fd.md) |

# Synthesis

In the current evidence, NVIDIA H200 is the clearest high-end single GPU record:
it combines 141 GB HBM3e, 4.8 TB/s memory bandwidth, and multi-petaflop
tensor/INT8 figures, but at a 600-700 W power envelope. Huawei Atlas 300I A2,
Cambricon MLU370, and Kunlunxin R200/RG800 expose more modest card-level
performance and memory, with power envelopes from 75 W to 350 W depending on
form factor.

The highest aggregate numbers are cloud/system records, not single cards. AWS
Trn2 and Huawei Atlas 800T A3 report multi-chip or multi-server totals, while
Kunlunxin R480-X8 reports an 8-module aggregate. These are useful capacity
planning records, but must be normalized before card-to-card comparison.

Several domestic GPU/AI accelerator vendors expose form factor and power more
clearly than compute peaks in the captured HTML. Biren and MetaX pages are
especially useful for deployment envelope comparison, while the structured
catalog should add observations later if official compute and memory tables are
captured.

DPU and SmartNIC records have a separate comparison axis. NVIDIA BlueField-3,
Yusur K2-Pro, Asterfusion Helium, Resnics Stargate, and Corigine Agilio are
infrastructure accelerators where network bandwidth, programmable packet
processing, storage offload, IOPS, and latency matter more than tensor FLOPS.

# Citations

- ../../data/compute_accelerators/skus/sample-skus.yaml
- ../../data/compute_accelerators/observations/sample-observations.yaml
- ../../data/compute_accelerators/resolved/sample-resolved-specs.yaml
- ../../raw/crawler/compute-accelerators-nvidia-h200/20260627T153310569545Z-www-nvidia-com-en-us-data-center-h200-7d05aa2873.md
- ../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-rel-2-19-3-html.md
- ../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-rel-2-18-3-html.md
- ../../raw/github/nvidia-nccl-closed-issues/api-pages/closed-issues-page-011.json.gz
- ../../raw/github/sgl-project-sglang-closed-issues-prs/comment-pages/issue-comments-page-205.json.gz
- ../../raw/crawler/compute-accelerators-aws-trn2/20260627T153315637188Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md
- ../../raw/crawler/compute-accelerators-huawei-atlas-300i-a2/20260628T055951712859Z-e-huawei-com-cn-products-computing-ascend-atlas-300i-a2-be2af90418.md
- ../../raw/crawler/compute-accelerators-huawei-atlas-800t-a3/20260628T060648300656Z-e-huawei-com-cn-products-computing-ascend-atlas-800t-a3-4a689659c8.md
- ../../raw/crawler/compute-accelerators-cambricon-mlu370-s4-s8/20260628T060442871520Z-www-cambricon-com-index-php-dd51e6b9e9.md
- ../../raw/crawler/compute-accelerators-cambricon-mlu370-x4/20260628T060443305596Z-www-cambricon-com-index-php-56612de611.md
- ../../raw/crawler/compute-accelerators-cambricon-mlu370-x8/20260628T060443731999Z-www-cambricon-com-index-php-da315093d5.md
- ../../raw/crawler/compute-accelerators-kunlunxin-r200/20260628T060651804777Z-www-kunlunxin-com-product-274-html-d12bf3953a.md
- ../../raw/crawler/compute-accelerators-kunlunxin-r480-x8/20260628T060652154506Z-www-kunlunxin-com-product-272-html-89686dc880.md
- ../../raw/crawler/compute-accelerators-kunlunxin-rg800/20260628T060652551492Z-www-kunlunxin-com-product-2842-html-6c65e115a3.md
- ../../raw/crawler/compute-accelerators-nvidia-bluefield-3/20260627T153315013778Z-www-nvidia-com-en-us-networking-products-data-processing-unit-d517920f8d.md
- ../../manifest-ai-infra-expansion-2026-07-07-r9-task-2-gap-proof.json
