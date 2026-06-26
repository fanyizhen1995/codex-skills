---
type: Reference
title: Compute Accelerator Field Glossary
description: Canonical field names, units, and scope applicability for accelerator specifications.
domain: ai_infra
status: reviewed
aliases:
  - accelerator field glossary
  - accelerator spec fields
tags:
  - accelerators
  - schema
  - specs
source_refs:
  - ../../data/compute_accelerators/schema/accelerator-scopes.yaml
  - ../../data/compute_accelerators/schema/spec-fields.yaml
---

# Summary

The catalog separates common fields, compute fields, and role-specific fields
so GPU, NPU, TPU, DPU, IPU, FPGA, DSA, and AI ASIC records can share one data
model without forcing every accelerator into GPU-style metrics.

# Field Groups

`common_specs` covers memory, bandwidth, power, form factor, host interface,
interconnect, software stack, and release information.

`compute_specs` covers FP64, FP32, TF32, BF16, FP16, FP8, INT8, TOPS/FLOPS,
matrix engines, sparse performance, and supported precision modes.

`role_specific_specs` covers DPU/IPU networking and offload fields, FPGA logic
resources, TPU deployment details, NPU/DSA compiler and operator support, and
cloud offering aggregate fields.

# Unit Policy

Resolved fields use canonical units from `spec-fields.yaml`. Observations can
preserve source wording in notes, but normalized values should use canonical
units such as `GB`, `TB/s`, `W`, `TFLOPS`, `TOPS`, `Gb/s`, and `count`.

# Citations

- ../../data/compute_accelerators/schema/accelerator-scopes.yaml
- ../../data/compute_accelerators/schema/spec-fields.yaml
