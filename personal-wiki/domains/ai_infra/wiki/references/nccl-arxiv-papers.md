---
type: Reference
title: NCCL Arxiv Papers
description: Page-level arXiv discovery captures for NCCL, collective communication, distributed training synchronization, and multi-node LLM inference research.
domain: ai_infra
status: reviewed
tags:
  - nccl
  - arxiv
  - collective-communication
  - distributed-training
  - inference-serving
source_refs:
  - ../../raw/crawler/manifest-20260705-20260707-scheduled-refresh.json
updated: 2026-07-08
aliases:
  - NCCL arXiv discovery
  - NCCL paper leads
related:
  - ../projects/nccl.md
  - nccl-technical-blog-network-observability.md
  - distributed-training-infrastructure.md
  - inference-runtime-infrastructure.md
---
# Summary

This reference indexes 25 arXiv abstract captures collected by the scheduled crawler on 2026-07-05. Treat this page as a discovery map, not as a peer-review or implementation-quality judgment. The captures are useful for finding research leads around NCCL-level communication strategy, GPU collective compression, heterogeneous collective libraries, distributed training synchronization, node-interconnect balancing, GPU-initiated networking, and multi-node LLM inference communication.

The arXiv captures are not production incident evidence and do not replace the official NCCL release notes, GitHub issue corpus, or NVIDIA technical-blog sources. Promote a paper into a dedicated paper page only after reading the full paper or PDF and checking whether the claim is relevant to local AI infrastructure decisions.

# Capture Scope

| Item | Value |
| --- | --- |
| Source profile | `nccl-arxiv-papers` |
| Raw captures | 25 Markdown arXiv abstract snapshots |
| Capture date | 2026-07-05 |
| Boundary | Discovery leads for communication, synchronization, inference serving, and GPU cluster research |
| Non-goal | No benchmark claims are promoted from abstracts alone |

# Discovery Leads

| Paper | Infrastructure surface | Raw |
| --- | --- | --- |
| HSAP: A Hierarchical Sequence-aware Parallelism for Hybrid-Context Generative Models | NCCL-level communication strategy for hybrid-context sequence parallelism and JIT-optimized device-group communication | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041098758Z-arxiv-org-abs-2606-30460v2-d5e473afa2.md) |
| TurboServe: Serving Streaming Video Generation Efficiently and Economically | Streaming video-generation serving efficiency and cost | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041099351Z-arxiv-org-abs-2606-19271v1-06869b6f1d.md) |
| StageFrontier: Synchronization-Aware Stage Accounting for Distributed ML Training | Stage accounting and synchronization overhead diagnosis for distributed ML training | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041099680Z-arxiv-org-abs-2606-06751v1-b5a3b13bb1.md) |
| Don't Let a Few Network Failures Slow the Entire AllReduce | AllReduce behavior under asymmetric or degraded network bandwidth | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041099951Z-arxiv-org-abs-2606-01680v1-8a71831dfd.md) |
| HetCCL: Enabling Collective Communication For Mixed-Vendor Heterogeneous Clusters | Heterogeneous collective communication across mixed-vendor accelerators | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041100202Z-arxiv-org-abs-2605-31000v1-2a6a167728.md) |
| Profiling-Driven Adaptive Distributed Transformer Inference on Embedded Edge Deployment | Distributed transformer inference on constrained edge deployments | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041100477Z-arxiv-org-abs-2605-25682v1-949624d2c1.md) |
| Guard: Scalable Straggler Detection and Node Health Management for Large-Scale Training | Straggler detection and node health management | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041100743Z-arxiv-org-abs-2605-17879v1-be87df8c99.md) |
| NCCLZ: Compression-Enabled GPU Collectives with Decoupled Quantization and Entropy Coding | Compression-enabled GPU collective communication | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041100999Z-arxiv-org-abs-2605-12396v1-2e61bea855.md) |
| DITRON: Distributed Multi-level Tiling Compiler for Parallel Tensor Programs | Compiler support for distributed tensor programs | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041101494Z-arxiv-org-abs-2605-02953v1-d008edec45.md) |
| UCCL-Zip: Lossless Compression Supercharged GPU Communication | Lossless compression for GPU communication | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041101759Z-arxiv-org-abs-2604-17172v2-4fd0057150.md) |
| From Skew to Symmetry: Node-Interconnect Multi-Path Balancing with Execution-time Planning for Modern GPU Clusters | Multi-path balancing and execution-time planning for GPU cluster interconnects | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041102248Z-arxiv-org-abs-2604-00317v1-026bd2fb1c.md) |
| SysOM-AI: Continuous Cross-Layer Performance Diagnosis for Production AI Training | Cross-layer performance diagnosis for production AI training | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041102501Z-arxiv-org-abs-2603-29235v1-00198cf584.md) |
| NCCL EP: Towards a Unified Expert Parallel Communication API for NCCL | Expert-parallel communication API boundary for NCCL | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041102733Z-arxiv-org-abs-2603-13606v3-40e4a7e76a.md) |
| NCCLbpf: Verified, Composable Policy Execution for GPU Collective Communication | Policy execution and verification for GPU collective communication | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041103236Z-arxiv-org-abs-2603-11438v2-00c44c828b.md) |
| Lagom: Unleashing the Power of Communication and Computation Overlapping for Distributed LLM Training | Communication/computation overlap for distributed LLM training | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041103489Z-arxiv-org-abs-2602-20656v1-05fce735af.md) |
| DynamiQ: Accelerating Gradient Synchronization using Compressed Multi-hop All-reduce | Compressed multi-hop all-reduce for gradient synchronization | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041103731Z-arxiv-org-abs-2602-08923v1-f7c0a77012.md) |
| HetCCL: Accelerating LLM Training with Heterogeneous GPUs | Heterogeneous-GPU LLM training communication | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041103962Z-arxiv-org-abs-2601-22585v1-632ac02ac2.md) |
| FUSCO: High-Performance Distributed Data Shuffling via Transformation-Communication Fusion | Distributed data shuffling and transformation/communication fusion | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041104193Z-arxiv-org-abs-2512-22036v1-d24606e26b.md) |
| SHIFT: Exploring the Boundary of RDMA Network Fault Tolerance | RDMA network fault-tolerance boundary | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041104435Z-arxiv-org-abs-2512-11094v2-759528ed7b.md) |
| GPU-Initiated Networking for NCCL | GPU-initiated networking in NCCL communication | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041104894Z-arxiv-org-abs-2511-15076v2-5118b66b29.md) |
| Understanding and Improving Communication Performance in Multi-node LLM Inference | Multi-node LLM inference communication performance | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041105117Z-arxiv-org-abs-2511-09557v4-ef4b64b915.md) |

# Lower-Priority Or Off-Boundary Captures

Four captures are kept in the raw manifest but are lower-priority for this domain unless a later task finds an infrastructure-specific angle: GPU-accelerated simulations, MPI-Q classical-quantum hybrid communication, HPC containers for EBRAINS, and DLRM embedding-bag inference performance. They remain searchable through the manifest and raw paths without being promoted into operational claims.

# Retrieval Notes

Use the manifest for exact capture accounting and the raw files for abstracts, authors, publication dates, and arXiv URLs. Use [NCCL Technical Blog Network Observability](nccl-technical-blog-network-observability.md), [NCCL Release Notes](nccl-release-notes.md), and [NCCL GitHub Closed Issues](nccl-github-closed-issues.md) for implementation, release, and field-troubleshooting evidence.

# Citations

- [AI infra scheduled crawler refresh manifest, 2026-07-05 to 2026-07-07](../../raw/crawler/manifest-20260705-20260707-scheduled-refresh.json)
