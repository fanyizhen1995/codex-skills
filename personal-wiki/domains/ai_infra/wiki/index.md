---
type: Index
title: ai_infra Index
description: Generated index for ai_infra.
domain: ai_infra
---

# ai_infra Index

## Concepts

- [NVIDIA Green Context](concepts/nvidia-green-context.md) - CUDA Green Context evidence in local AI infrastructure sources, centered on SGLang spatial multiplexing and CUDA compatibility issues.

## Papers

- [The Hitchhiker's Guide to Agentic AI](papers/hitchhikers-guide-agentic-ai.md) - Large 2026 guide spanning LLM foundations, AI systems, evaluation, and the agentic AI runtime stack.

## Projects

- [Compute Accelerator Crawler](projects/compute-accelerator-crawler.md) - Crawler source profile conventions for accelerator specification discovery and candidate extraction.
- [Compute Accelerator Spec Catalog](projects/compute-accelerator-spec-catalog.md) - Structured catalog for source-backed GPU, NPU, TPU, DPU, IPU, FPGA, DSA, and AI ASIC specifications.
- [Kubernetes](projects/kubernetes.md) - Container orchestration project whose scheduler, node, API machinery, and device-management issue history is relevant to AI infrastructure operations.
- [Kueue](projects/kueue.md) - Kubernetes-native job queueing project for quota-aware batch and AI workloads.
- [NCCL](projects/nccl.md) - NVIDIA's topology-aware collective communication library for multi-GPU and multi-node AI workloads.
- [SGLang](projects/sglang.md) - Inference serving and runtime system for large language and multimodal model workloads.
- [Volcano](projects/volcano.md) - Kubernetes-native batch scheduling project for high-performance and AI workloads.

## Decisions

_No pages yet._

## References

- [AI Infra Coverage Map](references/ai-infra-coverage-map.md) - Durable navigation point for the autonomous AI infrastructure coverage scan and remaining gaps.
- [Compute Accelerator Crawl Inventory](references/compute-accelerator-crawl-inventory.md) - Inventory of raw crawler captures for compute accelerator discovery and specification evidence.
- [Compute Accelerator Field Glossary](references/compute-accelerator-field-glossary.md) - Canonical field names, units, and scope applicability for accelerator specifications.
- [Compute Accelerator Parameter Comparison](references/compute-accelerator-parameter-comparison.md) - Current cross-vendor parameter comparison for accelerator, cloud offering, system, DPU, and SmartNIC records captured in ai_infra.
- [Compute Accelerator Spec Sources](references/compute-accelerator-spec-sources.md) - Source ranking and provenance policy for the compute accelerator specification catalog.
- [Data RAG Pipeline Infrastructure](references/data-rag-pipeline-infrastructure.md) - Source-backed reference for data/RAG ingestion, workflow orchestration, embedding workers, table lifecycle, metadata lineage, and RAG observability beyond vector index mechanics.
- [Data RAG Vector Infrastructure](references/data-rag-vector-infrastructure.md) - Source-backed reference for vector database, retrieval, and embedding-index infrastructure across Milvus, Qdrant, Weaviate, pgvector, and FAISS.
- [Distributed Training Infrastructure](references/distributed-training-infrastructure.md) - Source-backed reference for distributed training framework lifecycle, sharding, checkpointing, elastic restart, and training job boundaries beyond NCCL communication.
- [Evaluation Observability Reliability Infrastructure](references/evaluation-observability-reliability-infrastructure.md) - Source-backed reference for LLM evaluation harnesses, GenAI tracing, alerting mechanics, observability platforms, and platform profiling signals.
- [Inference Runtime Infrastructure](references/inference-runtime-infrastructure.md) - Source-backed reference for inference serving runtime mechanics and deployment controls across vLLM, TensorRT-LLM, Triton Inference Server, llama.cpp, ONNX Runtime GenAI, Ray Serve, Knative, and local TensorRT/vLLM captures.
- [Kubernetes, Volcano, And Kueue GitHub Closed Issues](references/kubernetes-volcano-kueue-github-closed-issues.md) - Local raw corpus and monthly sync setup for closed GitHub issues from Kubernetes, Volcano, and Kueue.
- [NCCL Arxiv Papers](references/nccl-arxiv-papers.md) - Page-level arXiv discovery captures for NCCL, collective communication, distributed training synchronization, and multi-node LLM inference research.
- [NCCL GitHub Closed Issues](references/nccl-github-closed-issues.md) - Local raw corpus and curated operational signals from closed NVIDIA/nccl GitHub issues and issue comments.
- [NCCL Release Notes](references/nccl-release-notes.md) - Complete local catalog of official NVIDIA NCCL release-note pages from 2.30.7 back to 2.0.2.
- [NCCL Technical Blog Network Observability](references/nccl-technical-blog-network-observability.md) - Local NVIDIA technical-blog evidence for NCCL Inspector, Prometheus observability, Spectrum-X/RoCE convergence, NCCL reliability, SHARP, NVBandwidth, and cost-estimation signals.
- [Network Storage Cluster Infrastructure](references/network-storage-cluster-infrastructure.md) - Source-backed reference for AI cluster networking, parallel/shared storage, distributed storage, and storage-fabric boundaries beyond NCCL and accelerator SKU tables.
- [Orchestration Scheduling Infrastructure](references/orchestration-scheduling-infrastructure.md) - Source-backed reference for Ray/KubeRay, Slurm GPU scheduling, Kubernetes device plugins, GPU operators, Kubernetes-native training jobs, and accelerator quota boundaries.
- [Security Governance Cost Infrastructure](references/security-governance-cost-infrastructure.md) - Source-backed reference for AI platform tenant isolation, accelerator sharing governance, quota controls, cost attribution, and capacity planning.
- [SGLang GitHub Closed Issues And PRs](references/sglang-github-closed-issues-prs.md) - Local raw corpus and curated operational signals from closed sgl-project/sglang GitHub issues, pull requests, comments, and review comments.
