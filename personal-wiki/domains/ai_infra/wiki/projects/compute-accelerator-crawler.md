---
type: Project
title: Compute Accelerator Crawler
description: Crawler source profile conventions for accelerator specification discovery and candidate extraction.
domain: ai_infra
status: reviewed
aliases:
  - accelerator crawler
  - accelerator source profiles
tags:
  - accelerators
  - crawler
  - ingestion
source_refs:
  - ../../data/compute_accelerators/candidates/README.md
  - ../../data/compute_accelerators/sources/source-registry.yaml
---

# Summary

Compute accelerator crawler profiles discover source changes and write raw
snapshots plus candidate structured records. They do not directly overwrite
resolved specifications.

# Profile Metadata

Each accelerator source profile includes source rank, accelerator scope,
extract mode, vendor hint, and auto-resolve policy. `extract_mode:
specs_candidate` means the crawler writes candidate data for later validation.

# Review Boundary

High-trust official sources can produce observations when extraction is clear.
Cloud sources update cloud offering fields. Third-party sources stay pending
review and cannot auto-resolve without `reviewed_by`.

# Citations

- ../../data/compute_accelerators/candidates/README.md
- ../../data/compute_accelerators/sources/source-registry.yaml
