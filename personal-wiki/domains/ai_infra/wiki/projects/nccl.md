---
type: Project
title: NCCL
description: NVIDIA's topology-aware collective communication library for multi-GPU and multi-node AI workloads.
domain: ai_infra
status: draft
tags:
  - nccl
  - gpu-communication
  - distributed-training
  - collective-communication
source_refs:
  - ../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-index-html.md
  - ../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-rel-2-30-7-html.md
updated: 2026-06-24
aliases:
  - NVIDIA Collective Communications Library
  - NVIDIA NCCL
related:
  - ../references/nccl-release-notes.md
---
# Summary

NCCL is NVIDIA's library for topology-aware multi-GPU collective communication primitives. In the AI infrastructure domain, it belongs with distributed training and inference runtime infrastructure because collective communication behavior affects cluster utilization, scaling efficiency, failure modes, and upgrade risk.

# Architecture

NVIDIA describes NCCL as focused on accelerating collective communication primitives rather than as a full parallel-programming framework. The release-note corpus tracks runtime and packaging compatibility, key feature additions, fixed issues, and known issues across NCCL releases.

# Usage

- Use [NCCL Release Notes](../references/nccl-release-notes.md) before upgrading NCCL in training or inference clusters.
- Check each target release's compatibility section for CUDA and packaging support.
- Check fixed and known issues for behavior that can affect multi-node jobs, GPU Direct paths, collectives, and runtime stability.

# Relationships

- [NCCL Release Notes](../references/nccl-release-notes.md) catalogs all official per-version release-note pages captured from NVIDIA.

# Open Questions

- Add cluster-specific upgrade notes when local workloads expose NCCL behavior that is not fully described by the official release notes.

# Citations

- [Official NCCL release-note index](../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-index-html.md)
- [Latest captured NCCL release note](../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-rel-2-30-7-html.md)
