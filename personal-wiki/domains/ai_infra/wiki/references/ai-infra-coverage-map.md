---
type: Reference
title: AI Infra Coverage Map
description: Durable navigation point for the autonomous AI infrastructure coverage scan and remaining gaps.
domain: ai_infra
status: reviewed
aliases:
  - ai_infra coverage map
  - AI infrastructure coverage map
tags:
  - coverage-map
  - autonomous-knowledge
  - ai-infrastructure
source_refs:
  - ../../coverage-map.json
  - ../../loop-state.json
  - ../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-index-html.md
  - ../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-summary.json
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-summary.json
  - ../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-summary.json
  - ../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-summary.json
  - ../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-summary.json
  - ../../raw/crawler/manual-url-arxiv-org-pdf-2606-24937-02f2168fd4/20260630T012708593204Z-arxiv-org-pdf-2606-24937-9d7a5b6fec.md
  - ../../raw/crawler/compute-accelerator-discovery-nvidia-products/20260628T055950730327Z-www-nvidia-com-en-us-data-center-products-200b75abd8.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704293693Z-developer-nvidia-com-blog-real-time-performance-monitoring-and-faster-debugging-with-nccl-52ce17cc71.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704297319Z-developer-nvidia-com-blog-ai-fabric-resiliency-and-why-network-convergence-matters-2d9246e4ca.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704298674Z-developer-nvidia-com-blog-memory-efficiency-faster-initialization-and-cost-estimation-with-32a1d0c118.md
  - ../../raw/links/milvus-architecture-overview-20260707.md
  - ../../raw/links/qdrant-indexing-official-docs-20260707.md
  - ../../raw/links/weaviate-vector-indexing-official-docs-20260707.md
  - ../../raw/links/pgvector-readme-official-20260707.md
  - ../../raw/links/faiss-readme-and-indexes-official-20260707.md
  - ../../raw/links/ray-data-pipeline-official-docs-20260707.md
  - ../../raw/links/apache-flink-stateful-stream-processing-official-docs-20260707.md
  - ../../raw/links/huggingface-text-embeddings-inference-official-docs-20260707.md
  - ../../raw/links/datahub-openlineage-metadata-lineage-official-docs-20260707.md
  - ../../raw/links/langfuse-rag-observability-official-docs-20260707.md
  - ../../raw/links/vllm-readme-official-20260707.md
  - ../../raw/links/tensorrt-llm-kv-cache-official-docs-20260707.md
  - ../../raw/links/triton-inference-server-batcher-official-docs-20260707.md
  - ../../raw/links/llama-cpp-server-official-docs-20260707.md
  - ../../raw/links/onnx-runtime-genai-config-official-docs-20260707.md
  - ../../raw/links/opentelemetry-genai-semconv-official-20260707.md
  - ../../raw/links/langsmith-observability-evaluation-official-20260707.md
  - ../../raw/links/phoenix-evaluation-tracing-official-20260707.md
  - ../../raw/links/ragas-evaluation-metrics-official-20260707.md
  - ../../raw/links/lm-evaluation-harness-official-20260707.md
  - ../../raw/links/nvidia-dcgm-gpu-telemetry-official-20260707.md
  - ../../raw/links/nvidia-nsight-systems-profiling-official-20260707.md
  - ../../manifest-ai-infra-expansion-2026-07-06-r5-task-1-gap-proof.json
  - ../../raw/crawler/compute-accelerator-discovery-amd-instinct/20260706T203709866943Z-www-amd-com-en-products-accelerators-instinct-html-d416b602fe.md
  - ../../raw/crawler/compute-accelerators-cambricon-mlu370-s4-s8/20260706T204119753429Z-www-cambricon-com-index-php-dd51e6b9e9.md
  - ../../raw/crawler/nccl-nvidia-blog-wide/20260626T015710841547Z-developer-nvidia-com-blog-one-click-multi-tenant-security-with-nvidia-quantum-infiniband-5b2cd4e1d4.md
  - ../../raw/links/nvidia-gpu-isolation-confidential-computing-official-20260707.md
  - ../../raw/links/kubernetes-kueue-quota-governance-official-20260707.md
  - ../../raw/links/opencost-cost-attribution-official-20260707.md
  - ../../raw/links/aws-accelerator-capacity-quota-planning-official-20260707.md
  - ../../raw/links/aws-efa-ai-cluster-networking-official-20260707.md
  - ../../raw/links/aws-fsx-lustre-parallel-filesystem-official-20260707.md
  - ../../raw/links/weka-ai-storage-architecture-official-20260707.md
  - ../../raw/links/ceph-distributed-storage-official-docs-20260707.md
  - ../../raw/links/spdk-nvme-of-target-official-docs-20260707.md
updated: 2026-07-07
related:
  - ../projects/nccl.md
  - ../references/nccl-technical-blog-network-observability.md
  - ../references/network-storage-cluster-infrastructure.md
  - ../references/security-governance-cost-infrastructure.md
  - ../references/data-rag-vector-infrastructure.md
  - ../references/data-rag-pipeline-infrastructure.md
  - ../references/inference-runtime-infrastructure.md
  - ../references/evaluation-observability-reliability-infrastructure.md
  - ../projects/sglang.md
  - ../references/kubernetes-volcano-kueue-github-closed-issues.md
  - ../references/compute-accelerator-crawl-inventory.md
  - ../papers/hitchhikers-guide-agentic-ai.md
---
# Summary

This page makes the autonomous `ai_infra` coverage scan discoverable from the curated wiki. The machine-readable state lives in [coverage-map.json](../../coverage-map.json) and [loop-state.json](../../loop-state.json); this page is the human navigation entry point.

The scan reuses existing local evidence and now treats the tracked 20260706 compute accelerator baseline as reconciled hardware evidence rather than unreconciled input. Current coverage is strongest for NCCL communication and NCCL-adjacent observability/fabric evidence, Kubernetes-native scheduling corpora, and compute accelerator raw inventory. Inference-runtime now has multi-project primary-source coverage through vLLM, TensorRT-LLM, Triton Inference Server, llama.cpp, ONNX Runtime GenAI, and local TensorRT/vLLM captures. Data/RAG/vector infrastructure has partial primary-source coverage through Milvus, Qdrant, Weaviate, pgvector, and FAISS source notes plus Ray Data, Flink, TEI, DataHub/OpenLineage, and Langfuse pipeline sources. Evaluation/observability/reliability now has general LLM tracing, evaluation-harness, and platform profiling coverage through OpenTelemetry GenAI, LangSmith, Phoenix, Ragas, lm-evaluation-harness, DCGM, and Nsight Systems source notes. Security/governance/cost now has source-backed coverage for tenant isolation, accelerator sharing, quota governance, workload cost allocation, and accelerator capacity planning. Network/storage/cluster coverage now adds EFA, FSx for Lustre, WEKA, Ceph, and SPDK NVMe-oF source notes while reusing Spectrum-X/RoCE and local DPU/NVMe-oF evidence. Both layers remain partial where incident, topology, benchmark, cross-cloud chargeback, and governance-policy evidence is still thin.

# Layer Status

| Layer | Current local coverage | Next gap |
| --- | --- | --- |
| `training-distributed` | NCCL release notes, closed GitHub issues, and technical-blog captures cover collective communication, SHARP offload, dynamic communicators, reliability, and cost-estimation hooks. | Add source-backed training framework, checkpointing, and elastic training pages beyond NCCL. |
| `inference-runtime` | SGLang issue/PR corpora and CUDA Green Context evidence cover serving runtime behavior and compatibility risks; [Inference Runtime Infrastructure](inference-runtime-infrastructure.md) adds vLLM, TensorRT-LLM, Triton Inference Server, llama.cpp, ONNX Runtime GenAI, and local TensorRT/vLLM runtime evidence for batching, KV-cache lifecycle, model repository/config loading, OpenAI-compatible serving, provider selection, and distributed inference knobs. | Add production router/admission-control, autoscaling, model-placement, rollout, benchmark, tracing, and incident/postmortem sources. |
| `orchestration-scheduling` | Kubernetes, Volcano, and Kueue closed-issue corpora cover scheduler, queueing, and cluster operations with comment-completeness caveats. | Add Ray, Slurm-on-Kubernetes, device plugins, and GPU quota/operator sources. |
| `data-rag-vector` | The Hitchhiker paper gives broad RAG context. [Data RAG Vector Infrastructure](data-rag-vector-infrastructure.md) covers vector database architecture, indexing, filtered retrieval, sparse retrieval, and embedding-index lifecycle. [Data RAG Pipeline Infrastructure](data-rag-pipeline-infrastructure.md) adds Ray Data batch/object-store pipelines, Flink checkpointed streaming refresh, TEI embedding worker boundaries, DataHub/OpenLineage metadata lineage, and Langfuse RAG tracing/evaluation. | Add direct Kafka Connect/Streams, workflow scheduler, object-store table-format governance, deletion/retention propagation, embedding drift policy, retrieval-quality alerting, and RAG incident sources. |
| `eval-observability-reliability` | The Hitchhiker paper covers agentic evaluation concepts; SGLang issues and NCCL issue/blog corpora supply reliability, debugging, NCCL Inspector, Prometheus/Grafana, RAS, NVBandwidth, and Spectrum-X telemetry evidence. [Evaluation Observability Reliability Infrastructure](evaluation-observability-reliability-infrastructure.md) adds OpenTelemetry GenAI telemetry schemas, LangSmith/Phoenix trace stores and experiments, Ragas and lm-evaluation-harness evaluation mechanics, and DCGM/Nsight platform telemetry/profiling. | Add production SLO, alerting, incident/postmortem, benchmark environment, non-NVIDIA platform, and evaluation data governance sources. |
| `security-governance-cost` | [Security Governance Cost Infrastructure](security-governance-cost-infrastructure.md) covers Quantum InfiniBand tenant isolation, MIG/vGPU accelerator sharing, NVIDIA confidential-computing attestation, Kubernetes ResourceQuota, Kueue ClusterQueue/ResourceFlavor/cohort governance, OpenCost workload cost allocation, AWS accelerator capacity/service-quota planning, and NCCL 2.22 cost-estimation boundaries. | Add evaluation-data governance, RAG access policy, cross-cloud chargeback, and incident/postmortem evidence. |
| `hardware-accelerator` | Compute accelerator inventory, field glossary, spec catalog, parameter comparison, and tracked July 6 baseline reconciliation cover GPU, NPU, TPU, DPU, IPU, FPGA, DSA, and AI ASIC evidence. | Fill unresolved fields only when product-specific pages, tables, datasheets, or PDFs provide source-backed values. |
| `network-storage-cluster` | [Network Storage Cluster Infrastructure](network-storage-cluster-infrastructure.md) adds AWS EFA, FSx for Lustre, WEKA, Ceph, and SPDK NVMe-oF source notes, while NCCL issue evidence, DPU/SmartNIC captures, and NCCL technical-blog captures cover RoCE, Spectrum-X, BGP PIC convergence, ECN/DC-QCN, SHARP, NIC Fusion, and fabric telemetry. | Add incident/postmortem, topology, storage benchmark, training/checkpoint case-study, and broader non-NVIDIA fabric operations evidence. |

# Use

Use [coverage-map.json](../../coverage-map.json) for planner/evaluator decisions. Use [loop-state.json](../../loop-state.json) for the current autonomous backlog and known source list. Do not record `stopped_no_action` while `candidate_backlog` remains non-empty.

# Citations

- [coverage-map.json](../../coverage-map.json)
- [loop-state.json](../../loop-state.json)
- [NCCL release-note index](../../raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-index-html.md)
- [NCCL closed issues summary](../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-summary.json)
- [SGLang closed issues and PRs summary](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-summary.json)
- [Kubernetes closed issues summary](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-summary.json)
- [Volcano closed issues summary](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-summary.json)
- [Kueue closed issues summary](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-summary.json)
- [Hitchhiker paper raw markdown](../../raw/crawler/manual-url-arxiv-org-pdf-2606-24937-02f2168fd4/20260630T012708593204Z-arxiv-org-pdf-2606-24937-9d7a5b6fec.md)
- [NVIDIA product discovery raw capture](../../raw/crawler/compute-accelerator-discovery-nvidia-products/20260628T055950730327Z-www-nvidia-com-en-us-data-center-products-200b75abd8.md)
- [r5 gap proof](../../manifest-ai-infra-expansion-2026-07-06-r5-task-1-gap-proof.json)
- [July 6 AMD Instinct discovery capture](../../raw/crawler/compute-accelerator-discovery-amd-instinct/20260706T203709866943Z-www-amd-com-en-products-accelerators-instinct-html-d416b602fe.md)
- [July 6 Cambricon MLU370-S4/S8 capture](../../raw/crawler/compute-accelerators-cambricon-mlu370-s4-s8/20260706T204119753429Z-www-cambricon-com-index-php-dd51e6b9e9.md)
- [Security Governance Cost Infrastructure](security-governance-cost-infrastructure.md)
- [NVIDIA Quantum InfiniBand multi-tenant security raw capture](../../raw/crawler/nccl-nvidia-blog-wide/20260626T015710841547Z-developer-nvidia-com-blog-one-click-multi-tenant-security-with-nvidia-quantum-infiniband-5b2cd4e1d4.md)
- [NVIDIA GPU isolation and confidential-computing source note](../../raw/links/nvidia-gpu-isolation-confidential-computing-official-20260707.md)
- [Kubernetes and Kueue quota governance source note](../../raw/links/kubernetes-kueue-quota-governance-official-20260707.md)
- [OpenCost cost allocation source note](../../raw/links/opencost-cost-attribution-official-20260707.md)
- [AWS accelerator capacity and service quota source note](../../raw/links/aws-accelerator-capacity-quota-planning-official-20260707.md)
- [Network Storage Cluster Infrastructure](network-storage-cluster-infrastructure.md)
- [AWS EFA source note](../../raw/links/aws-efa-ai-cluster-networking-official-20260707.md)
- [AWS FSx for Lustre source note](../../raw/links/aws-fsx-lustre-parallel-filesystem-official-20260707.md)
- [WEKA storage architecture source note](../../raw/links/weka-ai-storage-architecture-official-20260707.md)
- [Ceph distributed storage source note](../../raw/links/ceph-distributed-storage-official-docs-20260707.md)
- [SPDK NVMe-oF source note](../../raw/links/spdk-nvme-of-target-official-docs-20260707.md)
- [NCCL technical blog network observability reference](nccl-technical-blog-network-observability.md)
- [Data RAG Vector Infrastructure](data-rag-vector-infrastructure.md)
- [NCCL Inspector with Prometheus raw capture](../../raw/crawler/nccl-technical-blog/20260626T015704293693Z-developer-nvidia-com-blog-real-time-performance-monitoring-and-faster-debugging-with-nccl-52ce17cc71.md)
- [AI fabric resiliency raw capture](../../raw/crawler/nccl-technical-blog/20260626T015704297319Z-developer-nvidia-com-blog-ai-fabric-resiliency-and-why-network-convergence-matters-2d9246e4ca.md)
- [NCCL 2.22 cost-estimation raw capture](../../raw/crawler/nccl-technical-blog/20260626T015704298674Z-developer-nvidia-com-blog-memory-efficiency-faster-initialization-and-cost-estimation-with-32a1d0c118.md)
- [Milvus architecture source note](../../raw/links/milvus-architecture-overview-20260707.md)
- [Qdrant indexing source note](../../raw/links/qdrant-indexing-official-docs-20260707.md)
- [Weaviate vector indexing source note](../../raw/links/weaviate-vector-indexing-official-docs-20260707.md)
- [pgvector README source note](../../raw/links/pgvector-readme-official-20260707.md)
- [FAISS README and indexes source note](../../raw/links/faiss-readme-and-indexes-official-20260707.md)
- [Data RAG Pipeline Infrastructure](data-rag-pipeline-infrastructure.md)
- [Ray Data pipeline source note](../../raw/links/ray-data-pipeline-official-docs-20260707.md)
- [Apache Flink stateful stream-processing source note](../../raw/links/apache-flink-stateful-stream-processing-official-docs-20260707.md)
- [Hugging Face TEI source note](../../raw/links/huggingface-text-embeddings-inference-official-docs-20260707.md)
- [DataHub and OpenLineage metadata-lineage source note](../../raw/links/datahub-openlineage-metadata-lineage-official-docs-20260707.md)
- [Langfuse RAG observability source note](../../raw/links/langfuse-rag-observability-official-docs-20260707.md)
- [Inference Runtime Infrastructure](inference-runtime-infrastructure.md)
- [vLLM README source note](../../raw/links/vllm-readme-official-20260707.md)
- [TensorRT-LLM KV-cache and serve source note](../../raw/links/tensorrt-llm-kv-cache-official-docs-20260707.md)
- [Triton model repository and batcher source note](../../raw/links/triton-inference-server-batcher-official-docs-20260707.md)
- [llama.cpp source note](../../raw/links/llama-cpp-server-official-docs-20260707.md)
- [ONNX Runtime GenAI config/API source note](../../raw/links/onnx-runtime-genai-config-official-docs-20260707.md)
- [Evaluation Observability Reliability Infrastructure](evaluation-observability-reliability-infrastructure.md)
- [OpenTelemetry GenAI semantic conventions source note](../../raw/links/opentelemetry-genai-semconv-official-20260707.md)
- [LangSmith observability and evaluation source note](../../raw/links/langsmith-observability-evaluation-official-20260707.md)
- [Phoenix tracing and evaluation source note](../../raw/links/phoenix-evaluation-tracing-official-20260707.md)
- [Ragas evaluation metrics source note](../../raw/links/ragas-evaluation-metrics-official-20260707.md)
- [lm-evaluation-harness source note](../../raw/links/lm-evaluation-harness-official-20260707.md)
- [NVIDIA DCGM source note](../../raw/links/nvidia-dcgm-gpu-telemetry-official-20260707.md)
- [NVIDIA Nsight Systems source note](../../raw/links/nvidia-nsight-systems-profiling-official-20260707.md)
