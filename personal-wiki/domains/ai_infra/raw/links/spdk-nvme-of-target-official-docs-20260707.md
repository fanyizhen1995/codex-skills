---
type: RawSource
title: SPDK NVMe-oF Target Documentation
source_kind: web
url: https://spdk.io/doc/nvmf.html
captured: 2026-07-07
status: ingested
---
# Source

Official SPDK NVMe-oF documentation: https://spdk.io/doc/nvmf.html

Captured as a concise source note for `ai_infra` network-storage-cluster and storage-fabric coverage. The full external page was not mirrored; the durable facts below are paraphrased from the official source.

# Captured Facts

- SPDK documents an NVMe over Fabrics target that exposes NVMe subsystems and namespaces over fabric transports.
- The NVMe-oF target source is storage-fabric evidence: it explains how a host can access NVMe namespaces through a fabric target rather than only through local PCIe attachment.
- SPDK NVMe-oF belongs in the storage path layer. It should not be collapsed into accelerator SKU comparison unless the product source specifically exposes NVMe-oF hardware or offload behavior.
- NVMe-oF evidence complements local DPU/SmartNIC/NVMe-oF product captures by providing protocol and target-side behavior that is broader than a single vendor card.
- This source note should not be used for AI workload performance claims without a separate benchmark or deployment source that ties NVMe-oF behavior to the workload.

# Use In Wiki

Use this source note for source-backed claims about NVMe-oF storage fabrics, target/subsystem/namespace concepts, and the boundary between protocol behavior and product-specific storage-offload SKUs.
