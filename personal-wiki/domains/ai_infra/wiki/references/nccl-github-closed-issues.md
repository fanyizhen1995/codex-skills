---
type: Reference
title: NCCL GitHub Closed Issues
description: Local raw corpus and curated operational signals from closed NVIDIA/nccl GitHub issues and issue comments.
domain: ai_infra
status: reviewed
tags:
  - nccl
  - github-issues
  - troubleshooting
  - gpu-communication
  - distributed-training
source_refs:
  - ../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-with-comments.json.gz
  - ../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-summary.json
  - ../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-api-pages.json.gz
  - ../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-issue-comments-api-pages.json.gz
  - ../../raw/crawler/nccl-github-closed-issues/manifest-20260701-20260703.json
updated: 2026-07-04
aliases:
  - NVIDIA/nccl closed issues
  - NCCL GitHub issues
  - NCCL issue corpus
related:
  - ../projects/nccl.md
  - nccl-release-notes.md
---
# Summary

This reference indexes the local raw corpus for closed issues in the NVIDIA/nccl GitHub repository. The raw layer preserves the full GitHub API issue objects and issue-comment pages; this curated page keeps only the reusable scope, retrieval guidance, and operational signals.

Use this page as a field-evidence companion to [NCCL Release Notes](nccl-release-notes.md). Release notes are the canonical vendor change history; closed GitHub issues are better for user-reported integration cases, troubleshooting patterns, and upgrade-risk discovery.

# Corpus Scope

| Item | Value |
| --- | --- |
| Repository | `NVIDIA/nccl` |
| Included source | Closed GitHub issues, excluding pull requests |
| Issue capture | 19 GitHub issues API pages |
| Comment capture | 91 GitHub issue-comment API pages |
| Closed issues included | 1,589 |
| Pull requests excluded | 261 |
| Repository issue comments fetched | 9,093 |
| Comments attached to included closed issues | 7,325 |
| Issue/comment count mismatches | 0 |
| Issue created range | 2016-01-15 to 2026-06-22 |
| Issue closed range | 2016-01-25 to 2026-06-23 |
| Scheduled crawler supplement capture | 2 Markdown page snapshots captured 2026-07-01 and 2026-07-03 |

Raw files:

- [Joined closed issue and comment corpus](../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-with-comments.json.gz)
- [Derived summary](../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-summary.json)
- [Closed issue API pages](../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-api-pages.json.gz)
- [Issue comment API pages](../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-issue-comments-api-pages.json.gz)
- Per-page raw evidence under `raw/github/nvidia-nccl-closed-issues/api-pages/` and `raw/github/nvidia-nccl-closed-issues/comment-pages/`.
- [Scheduled crawler supplement manifest, 2026-07-01 and 2026-07-03](../../raw/crawler/nccl-github-closed-issues/manifest-20260701-20260703.json)

# Operational Signals

GitHub `state_reason` splits the included closed issues into 921 `completed` and 668 `not_planned` items. Treat this as an issue workflow signal: a closed issue is not automatically evidence of a product fix.

Labels are sparse in the historical closed issue set. The largest label counts are `question` with 79 issues, `bug` with 18, `triaged` with 16, and `enhancement` with 14. Use label filters when they exist, but do not rely on labels as a complete taxonomy.

Keyword-derived themes in the summary are retrieval aids and are not mutually exclusive. They point to common investigation surfaces: build and packaging, performance and scaling, API usage and integrations, network transport, GPU topology and platform behavior, and runtime failure debugging.

Closed-by-year counts are uneven, with 2025 dominating the captured closed set at 821 issues. Treat the year distribution as a repository process and triage signal, not as a direct defect-rate metric.

The 2026-07 scheduled crawler supplement adds two page-level issue snapshots after the API corpus cutoff. Issue #2226 is a question about GIN, GPI versus GDAKI, QP selection, and NIC support for GPU-initiated networking. Issue #2024 reports Ring Broadcast hangs above 16M elements with `cudaIpcMemLazyEnablePeerAccess` on H200/NVSwitch, separate processes, Ray, EFA, and NCCL 2.27.5. These are discovery leads for the next full GitHub API refresh; they are not yet joined with repository comments in the API corpus.

# Retrieval Notes

Use the joined raw corpus for issue-level lookup by issue number, title, state reason, label, comment count, and comment text. Use the summary JSON for aggregate counts, top-discussed issues, and broad theme entry points.

High-discussion examples in the captured corpus include:

| Issue | Comments | State reason | Topic |
| --- | ---: | --- | --- |
| #1013 | 90 | `not_planned` | `ncclCommAbort` stuck investigation |
| #340 | 37 | `completed` | NCCL 2.6.4 system hang report |
| #307 | 34 | `completed` | InfiniBand performance investigation |
| #622 | 32 | `not_planned` | Intel E810 `ncclSystemError` report |
| #257 | 31 | `completed` | AllReduce hang report |
| #1538 | 26 | `completed` | NCCL 2.22.3 core dump with RoCE version configuration |

# GPU Sharing And Multiplexing Issue Set

This is a manually filtered slice of the joined issue/comment raw corpus for GPU sharing, GPU multiplexing, MPS, MIG, vGPU, and VM-topology questions. The adjacent VM/vGPU entries are not all feature requests for same-GPU sharing; they are included because GPU partitioning, virtual PCI topology, ACS/ATS, SR-IOV, and vGPU layers change the P2P, GDR, and topology assumptions NCCL relies on.

Excluded false positives include generic `MIG M.` columns in `nvidia-smi` output, hostnames containing `VM`, CUDA `Integrated GPU sharing Host Memory` device-query lines, and ordinary one-process-per-GPU multi-process comparisons.

## Direct Same-GPU Sharing, MPS, And MIG

Reusable takeaway: historical NCCL issue answers generally assume one NCCL rank per physical CUDA device. Attempts to put multiple ranks or processes on the same GPU, or to reuse the same CUDA device in one communicator, are reported as unsupported, invalid usage, or hang-prone. Issue #1995 is different: it is a Q1 2026 roadmap item listing future multi-rank GPU and MPS support, not evidence that older releases supported the pattern.

| Issue | Closed | State reason | Relevance |
| --- | --- | --- | --- |
| #11 | 2019-05-06 | `completed` | Crashes with more than one communicator per GPU; comments discuss multiple ranks per GPU. |
| #32 | 2016-07-31 | `completed` | Direct question about multiple processes per GPU; comments discuss MPS, multiple ranks on one GPU, and two workers per GPU. |
| #39 | 2018-09-26 | `completed` | Torch hang with two workers per GPU; comment says CUDA MPS is required for multiple processes to share one GPU in that setup. |
| #46 | 2025-07-02 | `not_planned` | Notes/cookbook issue for using NCCL and MPS with Torch in multi-process, multi-GPU environments. |
| #103 | 2022-09-13 | `completed` | Single-GPU examples lead to multiple-process-per-GPU and MIG discussion; comments state multiple ranks on the same GPU are no longer supported since NCCL 2.5 and discuss MIG sub-GPU visibility limits. |
| #204 | 2025-07-02 | `not_planned` | Concurrent NCCL calls discuss MPS, GPU time sharing, and the warning that NCCL plus MPS was not supported because it could hang. |
| #231 | 2019-11-19 | `completed` | Same CUDA device used multiple times in one communicator; comments recommend one rank per GPU as the safe solution. |
| #418 | 2020-11-11 | `completed` | Direct question about multiple MPI ranks in the same GPU using NVIDIA Multi-Process Service; `ncclCommInitRank` returns invalid usage. |
| #431 | 2025-07-03 | `not_planned` | Feature request for two DDP workers on one large GPU; discusses A100/3090, MIG/sub-GPUs, and NCCL's one-rank-per-GPU topology assumption. |
| #1107 | 2023-12-16 | `completed` | Direct question about multiple MPI ranks per GPU in NCCL tests; answer says it is not currently supported. |
| #1995 | 2026-04-12 | `completed` | Roadmap lists support for multi-rank GPU and MPS support, marking the topic as a future/planned capability area. |

## vGPU, VM, And Virtualized Topology Adjacent Issues

Reusable takeaway: the virtualization set is about NCCL running under GPU passthrough, vGPU, Bitfusion-style GPU sharing, SR-IOV/VFIO, and virtualized PCI/NIC topology. These issues are relevant to GPU sharing and multiplexing infrastructure even when the immediate failure is P2P, GDR, RoCE, topology detection, or framework initialization rather than a same-GPU rank-sharing request.

| Issue | Closed | State reason | Relevance |
| --- | --- | --- | --- |
| #175 | 2019-05-06 | `completed` | QEMU GPU-passthrough VM with poor NCCL performance because GPU P2P could not be enabled. |
| #417 | 2020-11-10 | `completed` | PyTorch NCCL backend hang in a VM with multiple GPUs; disabling P2P avoided the hang. |
| #465 | 2021-02-25 | `completed` | RDMA/GPU Direct question where the reported PCI topology was virtual and flat inside a VM. |
| #575 | 2021-09-28 | `completed` | VMware Bitfusion VM case; maintainer notes GPU sharing between multiple VM instances is likely incompatible with NCCL's one-rank-per-physical-GPU assumption. |
| #603 | 2025-07-04 | `not_planned` | SR-IOV, VT-d/ACS, GPUDirect P2P/RDMA, and Kubernetes distributed-training hangs. |
| #660 | 2025-07-04 | `not_planned` | GDR test in a virtual machine; discussion centers on ACS requirements for GPU Direct RDMA inside a VM. |
| #749 | 2025-07-04 | `not_planned` | RoCE with dual HCA inside VMs and NCCL version sensitivity. |
| #811 | 2023-03-31 | `completed` | A100 GPU and IB SR-IOV passthrough to a KVM VM causing `all_reduce_perf` crash/topology issues. |
| #949 | 2023-08-10 | `completed` | A100 VM with SR-IOV VF passthrough; comments identify ACS/ATS as key for VM performance. |
| #1205 | 2024-03-01 | `completed` | `NCCL_IB_PCI_RELAXED_ORDERING` question; comments explain relaxed ordering matters with ACS+ATS inside VMs. |
| #1303 | 2025-07-19 | `not_planned` | H100 KVM+QEMU VMs with VFIO, SR-IOV VFs, GPU Direct, and RoCE performance issues. |
| #1329 | 2025-07-17 | `not_planned` | Virtual machine with multiple A800 GPUs where CUDA refused to enable P2P between GPUs. |
| #1373 | 2025-07-18 | `not_planned` | KubeVirt VM with GPUs and RDMA hitting NCCL panic under `nccl-tests`. |
| #1464 | 2025-07-17 | `not_planned` | VM topology, GDRDMA, PIX/PHB/PXB, and `NCCL_TOPO_FILE` guidance. |
| #1731 | 2025-06-06 | `completed` | VM/SR-IOV context for GDR plus `cudaMalloc` performance in a custom network plugin; adjacent virtualization pitfall even though NCCL itself could run at line rate. |
| #1843 | 2025-11-05 | `completed` | Best-practices question for creating `NCCL_TOPO_FILE` for KVM/libvirt VMs. |
| #2101 | 2026-04-26 | `completed` | VMware ESXi NVIDIA vGPU case where NCCL 2.27.5 failed during process-group initialization when UVM was disabled. |
| #2170 | 2026-05-22 | `completed` | Kubernetes plus vGPU plus vLLM tensor-parallel issue; triage says the observed failure likely came from PyTorch/socket handling rather than NCCL itself. |

# Relationships

- [NCCL](../projects/nccl.md) is the curated project page for the library.
- [NCCL Release Notes](nccl-release-notes.md) is the official vendor release-note catalog.

# Citations

- [NCCL closed GitHub issues with comments](../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-with-comments.json.gz)
- [NCCL closed GitHub issues summary](../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-summary.json)
- [NCCL closed issue API pages](../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-api-pages.json.gz)
- [NCCL issue comment API pages](../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-issue-comments-api-pages.json.gz)
- [NCCL scheduled crawler supplement manifest, 2026-07-01 and 2026-07-03](../../raw/crawler/nccl-github-closed-issues/manifest-20260701-20260703.json)
