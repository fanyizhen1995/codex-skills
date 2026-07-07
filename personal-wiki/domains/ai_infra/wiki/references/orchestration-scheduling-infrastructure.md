---
type: Reference
title: Orchestration Scheduling Infrastructure
description: Source-backed reference for Ray/KubeRay, Slurm GPU scheduling, Kubernetes device plugins, GPU operators, Kubernetes-native training jobs, and accelerator quota boundaries.
domain: ai_infra
status: reviewed
aliases:
  - orchestration scheduling infrastructure
  - AI workload scheduling infrastructure
  - accelerator orchestration infrastructure
tags:
  - orchestration-scheduling
  - scheduler
  - kubernetes
  - gpu-operator
source_refs:
  - ../../raw/links/ray-train-kuberay-official-docs-20260707.md
  - ../../raw/links/slurm-gpu-scheduling-official-docs-20260707.md
  - ../../raw/links/kubernetes-device-plugin-gpu-operators-official-docs-20260707.md
  - ../../raw/links/kubeflow-training-operator-official-docs-20260707.md
  - ../../raw/links/kubernetes-kueue-quota-governance-official-20260707.md
  - ../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-summary.json
  - ../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-summary.json
  - ../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-summary.json
updated: 2026-07-07
related:
  - ai-infra-coverage-map.md
  - distributed-training-infrastructure.md
  - kubernetes-volcano-kueue-github-closed-issues.md
  - security-governance-cost-infrastructure.md
---
# Summary

This page closes the local `orchestration-scheduling` backlog item that was broader than Kubernetes, Volcano, and Kueue issue corpora. It adds source-backed boundaries for Ray/KubeRay, Slurm GPU/GRES scheduling, Kubernetes device plugins, NVIDIA and AMD GPU operators, Kubeflow Trainer, and accelerator quota/operator interactions.

The key split is between admission, placement, device exposure, node lifecycle, and training job control. Kubernetes, Volcano, and Kueue issue corpora remain local operational evidence, but official source notes are needed to avoid treating sampled issues as full design documentation.

# Scheduler And Controller Surfaces

KubeRay defines Kubernetes custom resources for RayCluster, RayJob, and RayService. Those CRDs are the Kubernetes execution boundary for Ray workloads, while Ray Train remains the training API and checkpoint/fault-tolerance boundary. KubeRay docs also expose autoscaling, label-based scheduling, Kueue integration, Volcano integration, GPU use, observability, and troubleshooting topics. [raw](../../raw/links/ray-train-kuberay-official-docs-20260707.md)

Kubeflow Trainer is a Kubernetes-native training job controller surface. Its docs organize TrainJob lifecycle, runtime, job templates, ML policy, scheduling integration, and framework-specific guides for PyTorch, DeepSpeed, Megatron, JAX, XGBoost, and other training modes. Treat it as a controller layer above framework launchers. [raw](../../raw/links/kubeflow-training-operator-official-docs-20260707.md)

Slurm is the HPC scheduler boundary. Slurm GRES lets clusters model generic resources such as GPU types and counts, allocate them to jobs, and allocate job-step resources from the parent job allocation. That is scheduler evidence for GPU-bound training outside Kubernetes, and it should not be collapsed into Kubernetes queue semantics without a bridge source. [raw](../../raw/links/slurm-gpu-scheduling-official-docs-20260707.md)

# Device Plugins And GPU Operators

Kubernetes device plugins are the generic device exposure mechanism. They let vendors advertise hardware resources requiring vendor-specific setup to the kubelet, including GPUs, NICs, FPGAs, and non-volatile memory. This is the scheduler-visible resource boundary for accelerators. [raw](../../raw/links/kubernetes-device-plugin-gpu-operators-official-docs-20260707.md)

NVIDIA's Kubernetes device plugin is a DaemonSet that exposes GPU counts, tracks GPU health, and enables GPU-enabled containers. This source supports claims about resource discovery and device-plugin health signals, not full driver lifecycle management by itself. [raw](../../raw/links/kubernetes-device-plugin-gpu-operators-official-docs-20260707.md)

The NVIDIA GPU Operator is the broader node lifecycle boundary. It automates management of GPU software components such as drivers, the NVIDIA Kubernetes GPU device plugin, NVIDIA Container Toolkit, GPU Feature Discovery labels, DCGM monitoring, MIG Manager, validators, and related Kubernetes components. [raw](../../raw/links/kubernetes-device-plugin-gpu-operators-official-docs-20260707.md)

AMD GPU Operator is the non-NVIDIA operator source in this layer. Its documentation covers AMD Instinct accelerator deployment and management on Kubernetes, including driver management, AMD device plugin deployment, DRA support, metrics export, node labeling, resource allocation, health monitoring, and OpenShift/Kubernetes support. [raw](../../raw/links/kubernetes-device-plugin-gpu-operators-official-docs-20260707.md)

# Quota And Admission Boundaries

Kubernetes ResourceQuota is namespace-scoped aggregate resource governance, while Kueue ClusterQueues, ResourceFlavors, and cohorts express batch workload admission, quota pools, placement classes, and borrowing/lending rules. These controls are the quota/admission counterpart to the device-plugin and GPU-operator layer. [raw](../../raw/links/kubernetes-kueue-quota-governance-official-20260707.md)

The existing local Kueue issue corpus remains valuable operational evidence because it records queueing and quota-related issue history, but its joined comments are incomplete. Use official Kueue source notes for design claims and the GitHub corpus for observed field issues or regressions. [wiki](kubernetes-volcano-kueue-github-closed-issues.md)

# Local Operational Evidence

The Kubernetes, Volcano, and Kueue corpora already cover large local closed-issue sets: Kubernetes closed issues since 2023-07-01, all-time Volcano closed issues, and all-time Kueue closed issues. They support operational evidence for scheduler, queueing, device-plugin, and cluster behavior, with the important caveat that repository-level comment joins are incomplete for Kubernetes and Kueue. [raw](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-summary.json) [raw](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-summary.json) [raw](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-summary.json)

Local SGLang issue and PR titles mentioning Slurm, Megatron, FSDP, and AMD/Gaudi support are useful as discovery leads, but they are not promoted as orchestration design sources in this page. They remain inference/runtime operational signals unless a dedicated training or scheduling capture is later ingested.

# Duplicate Boundaries

This page does not duplicate [Security Governance Cost Infrastructure](security-governance-cost-infrastructure.md). That page covers quota governance, tenant isolation, cost attribution, and capacity planning. This page uses Kueue and ResourceQuota only to explain scheduler admission and accelerator placement boundaries.

This page does not replace [Distributed Training Infrastructure](distributed-training-infrastructure.md). PyTorch, DeepSpeed, Ray Train, and Kubeflow sources explain framework and TrainJob behavior there; this page focuses on schedulers, device exposure, operators, and Kubernetes/HPC execution surfaces.

# Coverage Use

Use this page as source-backed coverage for:

- `orchestration-scheduling`: Ray/KubeRay CRDs, RayJob/RayCluster execution, Slurm GPU/GRES scheduling, Kubernetes device plugins, NVIDIA and AMD GPU operators, Kubeflow Trainer job controllers, and quota/admission interactions with Kueue and ResourceQuota.
- `training-distributed`: only where KubeRay and Kubeflow explain training job controllers above framework runtimes.
- `security-governance-cost`: only where Kueue quota, ResourceFlavor, cohorts, or ResourceQuota explain admission and accelerator governance; use the security/governance page for cost and tenant isolation.
- `hardware-accelerator`: only where device plugins and GPU operators expose or manage accelerators; do not use this page for SKU parameters.

Remaining gaps for this layer are production scheduling incidents, cross-scheduler migration reports, Slurm-on-Kubernetes bridge deployments, scheduler benchmark evidence, and operator upgrade failure/postmortem evidence.

# Citations

- [Ray Train and KubeRay source note](../../raw/links/ray-train-kuberay-official-docs-20260707.md)
- [Slurm GPU and GRES scheduling source note](../../raw/links/slurm-gpu-scheduling-official-docs-20260707.md)
- [Kubernetes device plugin and GPU operators source note](../../raw/links/kubernetes-device-plugin-gpu-operators-official-docs-20260707.md)
- [Kubeflow Trainer source note](../../raw/links/kubeflow-training-operator-official-docs-20260707.md)
- [Kubernetes and Kueue quota governance source note](../../raw/links/kubernetes-kueue-quota-governance-official-20260707.md)
- [Kubernetes closed issues summary](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-summary.json)
- [Volcano closed issues summary](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-summary.json)
- [Kueue closed issues summary](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-summary.json)
