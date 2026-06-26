---
type: Reference
title: Compute Accelerator Spec Sources
description: Source ranking and provenance policy for the compute accelerator specification catalog.
domain: ai_infra
status: reviewed
aliases:
  - accelerator spec sources
  - compute accelerator source ranks
tags:
  - accelerators
  - provenance
  - specs
source_refs:
  - ../../data/compute_accelerators/schema/source-ranks.yaml
  - ../../data/compute_accelerators/sources/source-registry.yaml
---

# Summary

Compute accelerator specifications are resolved from field-level observations,
not copied directly from one flat table. Source rank controls whether a value
can become a resolved field automatically or must stay pending review.

# Source Ranks

- S1: official vendor specifications for card, module, chip, software, and
  support information.
- S2: official cloud provider documentation for instance, VM, node, and
  cloud-visible accelerator offerings.
- S3: standards, registries, and benchmark submissions.
- S4: runtime and inventory probe output.
- S5: third-party, media, procurement, analyst, and community sources that
  require review before resolution.

# Resolution Policy

S1 sources can resolve core single-accelerator fields when extraction is
unambiguous. S2 sources resolve cloud offering fields and do not overwrite
single-card vendor specs. S3 benchmark data stays benchmark-specific. S4 probe
data stays observed/runtime-specific. S5 data remains candidate-only unless a
reviewer is recorded.

# Citations

- ../../data/compute_accelerators/schema/source-ranks.yaml
- ../../data/compute_accelerators/sources/source-registry.yaml
