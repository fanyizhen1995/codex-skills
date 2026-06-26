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
---

# Summary

The compute accelerator spec catalog is the structured facts layer for
accelerator parameters in the `ai_infra` domain. It stores sample SKUs,
source-backed observations, and resolved fields with provenance.

# Current Coverage

The seed catalog validates the schema across representative GPU, NPU, TPU,
DPU, IPU, FPGA, DSA, and AI ASIC records. It intentionally leaves incomplete
public fields unresolved instead of inventing missing values.

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
