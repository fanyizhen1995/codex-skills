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
  - ../../raw/crawler/nccl-arxiv-papers/manifest-20260712-nccl-arxiv-refresh.json
  - ../../raw/crawler/nccl-arxiv-papers/20260712T041314410174Z-arxiv-org-abs-2607-07862v1-10bc5dfb1f.md
  - ../../raw/crawler/nccl-arxiv-papers/20260712T041314410768Z-arxiv-org-abs-2607-04676v1-dadf1c0894.md
  - ../../raw/crawler/nccl-arxiv-papers/20260712T041314411159Z-arxiv-org-abs-2602-08923v3-4ed352c0df.md
updated: 2026-07-16
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

This reference indexes scheduled arXiv abstract captures collected by the NCCL arXiv crawler: the initial 25-capture batch collected on 2026-07-05 plus a three-capture July 12 refresh. Treat this page as a discovery map, not as a peer-review or implementation-quality judgment. The captures are useful for finding research leads around NCCL-level communication strategy, GPU collective compression, heterogeneous collective libraries, distributed training synchronization, node-interconnect balancing, GPU-initiated networking, and multi-node LLM inference communication.

The arXiv captures are not production incident evidence and do not replace the official NCCL release notes, GitHub issue corpus, or NVIDIA technical-blog sources. Promote a paper into a dedicated paper page only after reading the full paper or PDF and checking whether the claim is relevant to local AI infrastructure decisions.

# Capture Scope

| Item | Value |
| --- | --- |
| Source profile | `nccl-arxiv-papers` |
| Raw captures | 25 Markdown arXiv abstract snapshots from the July 5 batch plus 3 Markdown abstract snapshots from the July 12 refresh |
| Capture date | 2026-07-05 and 2026-07-12 |
| Boundary | Discovery leads for communication, synchronization, inference serving, and GPU cluster research |
| Non-goal | No benchmark claims are promoted from abstracts alone |

# Discovery Leads

| Paper | Infrastructure surface | Raw |
| --- | --- | --- |
| CTA-Pipelining: A Latency-Oriented Spatial Scaling Method for Multi-GPU Systems | Abstract-level lead for latency-oriented multi-GPU spatial scaling for LLM serving on shared-memory H200/B200 systems using CUTLASS, cuBLAS, and NCCL | [raw](../../raw/crawler/nccl-arxiv-papers/20260712T041314410174Z-arxiv-org-abs-2607-07862v1-10bc5dfb1f.md) |
| Adaptive Space-efficient Collectives for Dynamic and Unstructured Sparsity on GPU Platforms | Abstract-level lead for sparse all-gather, reduce-scatter, and all-reduce collectives with bitvector-based Pici compression | [raw](../../raw/crawler/nccl-arxiv-papers/20260712T041314410768Z-arxiv-org-abs-2607-04676v1-dadf1c0894.md) |
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
| DynamiQ: Accelerating Gradient Synchronization using Compressed Multi-hop All-reduce | Compressed multi-hop all-reduce for gradient synchronization; July 12 capture is a v3 refresh of the existing `arxiv:2602.08923` lead, not a separate new paper | [v1 raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041103731Z-arxiv-org-abs-2602-08923v1-f7c0a77012.md), [v3 raw](../../raw/crawler/nccl-arxiv-papers/20260712T041314411159Z-arxiv-org-abs-2602-08923v3-4ed352c0df.md) |
| HetCCL: Accelerating LLM Training with Heterogeneous GPUs | Heterogeneous-GPU LLM training communication | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041103962Z-arxiv-org-abs-2601-22585v1-632ac02ac2.md) |
| FUSCO: High-Performance Distributed Data Shuffling via Transformation-Communication Fusion | Distributed data shuffling and transformation/communication fusion | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041104193Z-arxiv-org-abs-2512-22036v1-d24606e26b.md) |
| SHIFT: Exploring the Boundary of RDMA Network Fault Tolerance | RDMA network fault-tolerance boundary | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041104435Z-arxiv-org-abs-2512-11094v2-759528ed7b.md) |
| GPU-Initiated Networking for NCCL | GPU-initiated networking in NCCL communication | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041104894Z-arxiv-org-abs-2511-15076v2-5118b66b29.md) |
| Understanding and Improving Communication Performance in Multi-node LLM Inference | Multi-node LLM inference communication performance | [raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041105117Z-arxiv-org-abs-2511-09557v4-ef4b64b915.md) |

# Lower-Priority Or Off-Boundary Captures

Four captures are kept in the raw manifest but are lower-priority for this domain unless a later task finds an infrastructure-specific angle: GPU-accelerated simulations, MPI-Q classical-quantum hybrid communication, HPC containers for EBRAINS, and DLRM embedding-bag inference performance. They remain searchable through the manifest and raw paths without being promoted into operational claims.

# July 12 Refresh Boundary

The July 12 refresh adds two new abstract discovery identities and one version refresh. CTA-Pipelining `2607.07862v1` is new to the curated page and is useful as a serving-latency research lead: its abstract frames Cooperative Thread Array level pipelining as a spatial scaling method for LLM serving on 8-GPU H200 and B200 systems, using CUTLASS, cuBLAS, and NCCL, with source-stated latency reductions of up to 31.8% versus micro-batching and 29.6% versus tensor parallelism on a 2-layer GEMM MLP-shaped operation. Treat those numbers as abstract-stated claims only, not reproduced benchmarks or production guidance. [raw](../../raw/crawler/nccl-arxiv-papers/20260712T041314410174Z-arxiv-org-abs-2607-07862v1-10bc5dfb1f.md)

Adaptive Space-efficient Collectives `2607.04676v1` is also new to the curated page. Its abstract describes sparse all-gather, reduce-scatter, and all-reduce algorithms for GPU platforms, backed by a bitvector-based Pici format and adaptive sparse representations, with source-stated speedups over NCCL at 99% input sparsity. Treat those speedups as abstract discovery evidence only, not a replacement for NCCL implementation, release, benchmark, or production evidence. [raw](../../raw/crawler/nccl-arxiv-papers/20260712T041314410768Z-arxiv-org-abs-2607-04676v1-dadf1c0894.md)

DynamiQ `2602.08923v3` refreshes the existing DynamiQ row that was previously represented by `2602.08923v1`. The v3 abstract keeps the compressed multi-hop all-reduce and PyTorch DDP over NCCL P2P boundary, with source-stated improvement and near-baseline accuracy claims. Record it as a version refresh for the same unversioned arXiv identity, not as a separate new paper. [v1 raw](../../raw/crawler/nccl-arxiv-papers/20260705T041041103731Z-arxiv-org-abs-2602-08923v1-f7c0a77012.md) [v3 raw](../../raw/crawler/nccl-arxiv-papers/20260712T041314411159Z-arxiv-org-abs-2602-08923v3-4ed352c0df.md)

# Retrieval Notes

Use the manifests for exact capture accounting and the raw files for abstracts, authors, publication dates, and arXiv URLs. Use [NCCL Technical Blog Network Observability](nccl-technical-blog-network-observability.md), [NCCL Release Notes](nccl-release-notes.md), and [NCCL GitHub Closed Issues](nccl-github-closed-issues.md) for implementation, release, and field-troubleshooting evidence.

# Citations

- [AI infra scheduled crawler refresh manifest, 2026-07-05 to 2026-07-07](../../raw/crawler/manifest-20260705-20260707-scheduled-refresh.json)
- [NCCL arXiv papers July 12 refresh manifest](../../raw/crawler/nccl-arxiv-papers/manifest-20260712-nccl-arxiv-refresh.json)
- [CTA-Pipelining arXiv abstract capture](../../raw/crawler/nccl-arxiv-papers/20260712T041314410174Z-arxiv-org-abs-2607-07862v1-10bc5dfb1f.md)
- [Adaptive Space-efficient Collectives arXiv abstract capture](../../raw/crawler/nccl-arxiv-papers/20260712T041314410768Z-arxiv-org-abs-2607-04676v1-dadf1c0894.md)
- [DynamiQ v3 arXiv abstract capture](../../raw/crawler/nccl-arxiv-papers/20260712T041314411159Z-arxiv-org-abs-2602-08923v3-4ed352c0df.md)
