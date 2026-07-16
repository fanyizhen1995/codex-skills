---
type: Reference
title: Distributed Training Infrastructure
description: Source-backed reference for distributed training framework lifecycle, sharding, checkpointing, elastic restart, and training job boundaries beyond NCCL communication.
domain: ai_infra
status: reviewed
aliases:
  - distributed training infrastructure
  - training distributed infrastructure
  - distributed checkpointing infrastructure
tags:
  - training-distributed
  - distributed-training
  - checkpointing
  - elastic-training
source_refs:
  - ../../raw/links/pytorch-distributed-training-official-docs-20260707.md
  - ../../raw/links/deepspeed-megatron-training-official-sources-20260707.md
  - ../../raw/links/ray-train-kuberay-official-docs-20260707.md
  - ../../raw/links/kubeflow-training-operator-official-docs-20260707.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704295462Z-developer-nvidia-com-blog-building-scalable-and-fault-tolerant-nccl-applications-839bad0938.md
  - ../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-with-comments.json.gz
  - ../../raw/crawler/nccl-github-closed-issues/20260703T021318514537Z-github-com-nvidia-nccl-issues-2024-4e07290315.md
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-index.json
  - ../../raw/crawler/nccl-aws-ml-blog/20260705T041043512489Z-aws-amazon-com-blogs-machine-learning-how-outpost-vfx-uses-aws-to-accelerate-ai-model-trai-f1c01f6e54.md
  - ../../raw/crawler/nccl-aws-ml-blog/20260626T015712819063Z-aws-amazon-com-blogs-machine-learning-optimize-model-training-on-amazon-sagemaker-ai-with-14a08c4c5d.md
  - ../../raw/crawler/nccl-arxiv-papers/manifest-20260712-nccl-arxiv-refresh.json
  - ../../raw/crawler/nccl-arxiv-papers/20260712T041314410768Z-arxiv-org-abs-2607-04676v1-dadf1c0894.md
  - ../../raw/crawler/nccl-arxiv-papers/20260712T041314411159Z-arxiv-org-abs-2602-08923v3-4ed352c0df.md
updated: 2026-07-16
related:
  - ai-infra-coverage-map.md
  - nccl-github-closed-issues.md
  - nccl-technical-blog-network-observability.md
  - orchestration-scheduling-infrastructure.md
  - sglang-github-closed-issues-prs.md
---
# Summary

This page closes the local `training-distributed` backlog item that was still broader than NCCL. NCCL remains the source-backed communication layer; this reference adds framework lifecycle, sharding, checkpointing, elastic restart, and training job boundaries across PyTorch, DeepSpeed, Megatron-LM, Ray Train, and Kubeflow Trainer.

The common infrastructure pattern is a training job that has a launcher or controller, a distributed process group or worker group, model-state sharding, checkpoint save/load mechanics, and a restart/resume contract. Those surfaces are different from fabric telemetry or collective performance, so they are kept separate from [NCCL Technical Blog Network Observability](nccl-technical-blog-network-observability.md).

# Framework Runtime Boundaries

PyTorch provides the framework-level distributed runtime. Its distributed package defines communication backends and process group APIs, while `torchrun` launches workers with rendezvous metadata, rank/world-size environment variables, local process counts, and restart limits. This is the framework lifecycle boundary that NCCL alone does not cover. [raw](../../raw/links/pytorch-distributed-training-official-docs-20260707.md)

FSDP is the PyTorch sharding boundary. It wraps a module, shards parameters across data-parallel workers, and has strategies that shard parameters, gradients, and optimizer state. FSDP also changes state-dict behavior, so checkpoint design must account for full, sharded, local, and optimizer state dicts rather than assuming a single replicated model file. [raw](../../raw/links/pytorch-distributed-training-official-docs-20260707.md)

DeepSpeed adds a second sharding model. ZeRO partitions optimizer state, gradients, and model parameters across ranks in stages, and ZeRO-Infinity extends the placement boundary to CPU and NVMe offload. This belongs in training infrastructure because it changes accelerator memory pressure, checkpoint layout, and restart constraints. [raw](../../raw/links/deepspeed-megatron-training-official-sources-20260707.md)

Megatron-LM is tracked as primary project evidence for large-scale transformer training code and examples. In this page it is evidence that tensor/pipeline/data-parallel training systems have their own launcher, model partitioning, and checkpoint conversion boundaries; DeepSpeed-specific ZeRO behavior remains sourced to DeepSpeed documentation. [raw](../../raw/links/deepspeed-megatron-training-official-sources-20260707.md)

# Checkpointing And Recovery

Distributed checkpointing is a first-class infrastructure concern. PyTorch Distributed Checkpoint saves and loads from multiple ranks in parallel, creates multiple files per checkpoint, and supports load-time resharding so a checkpoint saved under one topology can be loaded under another. That makes checkpoint storage layout and topology change a framework contract, not just a filesystem concern. [raw](../../raw/links/pytorch-distributed-training-official-docs-20260707.md)

FSDP checkpointing has separate full, sharded, local, and optimizer state-dict modes. Rank-0-only full-state saves can reduce redundant memory use, while sharded state dicts keep checkpoint artifacts aligned with distributed state. Use the mode as part of the recovery design instead of assuming every training framework writes one portable file. [raw](../../raw/links/pytorch-distributed-training-official-docs-20260707.md)

DeepSpeed checkpointing covers model training checkpoint save/load, ZeRO fp32 weight recovery, ZeRO checkpoint conversion, checkpoint bloat mitigation, and Universal Checkpoints. Universal Checkpoints are specifically relevant to elastic hardware use because they aim to resume across different GPU counts for data, tensor, and pipeline parallel training, but the source marks that mechanism as under development. [raw](../../raw/links/deepspeed-megatron-training-official-sources-20260707.md)

Ray Train reports checkpoints from workers and restores the latest reported checkpoint through `ray.train.get_checkpoint()`. For multi-node failure tolerance, Ray's docs tie checkpoint recovery to shared storage such as cloud object storage or NFS, so the training job recovery boundary includes both Ray metadata and durable checkpoint storage. [raw](../../raw/links/ray-train-kuberay-official-docs-20260707.md)

# Elastic And Fault-Tolerant Launch

`torchrun` supports fixed-size fault-tolerant launches and elastic membership through rendezvous settings and `--max-restarts`. PyTorch documents that surviving workers are killed on failure or membership changes and a new worker group is formed, which means ranks and world size cannot be treated as stable in elastic runs. [raw](../../raw/links/pytorch-distributed-training-official-docs-20260707.md)

Ray Train handles worker and node failures through `FailureConfig`, worker-group restart, checkpoint restoration, and shared run state. Driver recovery depends on relaunching with the same run name and storage path so the latest checkpoint can be located. [raw](../../raw/links/ray-train-kuberay-official-docs-20260707.md)

The local NCCL fault-tolerant applications capture remains useful but narrower. It covers dynamic communicators, communicator shrink, and abort paths for collective communication. That evidence supports communication-level resilience, while PyTorch and Ray Train cover training script restart and checkpoint recovery. [raw](../../raw/crawler/nccl-technical-blog/20260626T015704295462Z-developer-nvidia-com-blog-building-scalable-and-fault-tolerant-nccl-applications-839bad0938.md)

# Local Operational Failure Evidence

The local NCCL issue corpus gives issue-level operational evidence for failure handling around the framework contracts above. Issue #998 discusses NCCL connection failover and records the operational boundary that an application should either stop and restart from the latest checkpoint or tear down and recreate communicators with an external health-detection system. Treat that as failure-mode evidence, not proof that any framework automatically recovers without checkpoint storage and restart orchestration. [raw](../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-with-comments.json.gz)

NCCL issue #2024 is a page-level crawler supplement after the API corpus cutoff. It reports a Ray separate-process workload on two AWS P5en nodes with H200/NVSwitch, EFA, NCCL 2.27.5, PyTorch 2.x, and CUDA 12.x where Ring broadcast hangs above 16M elements when lazy IPC peer access is used; the same report says Tree AllReduce and torchrun broadcast worked for the large test size. This is useful benchmark-shaped incident evidence for topology, launch mode, and collective algorithm interactions, but it is a single closed issue rather than a general benchmark result. [raw](../../raw/crawler/nccl-github-closed-issues/20260703T021318514537Z-github-com-nvidia-nccl-issues-2024-4e07290315.md)

Other selected NCCL issues show version and configuration-sensitive failure modes: #863 reports `ncclCommAbort` hanging after an upgrade to NCCL 2.16.5; #1538 reports an NCCL 2.22.3 core dump when `NCCL_IB_ROCE_VERSION_NUM` is set, and the local summary records it as a labeled bug/fixed issue; #1013 records a multi-ProcessGroup `ncclCommAbort` stuck investigation. These issues deepen the operational layer with upgrade, environment, and abort-path examples while still leaving production postmortems and measured restore-time evidence as gaps. [raw](../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-with-comments.json.gz)

The SGLang corpus remains a discovery boundary for adjacent runtime and training-integration issues rather than a primary training framework source. Its index includes FSDP, Megatron, Slurm, Gaudi, AMD/MI300, distributed, and checkpoint-related items; these titles are useful leads for future focused ingestion, but this page only uses them as evidence that downstream runtimes surface training and scheduler integration risks. [raw](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-index.json)

# AWS Training Case Study And Blackwell Tuning Boundaries

The Outpost VFX AWS blog capture is case-study evidence for moving a VFX face-replacement fine-tuning workflow from local RTX 3090 and G5-style single-GPU baselines toward distributed training on Amazon EC2 P5 instances with NVIDIA H100 GPUs. The source-visible implementation boundary is PyTorch Distributed Data Parallel on P5, with a comparison that fixed model hyperparameters and measured time to a loss threshold. The promoted result is bounded to the source claim: up to 8x faster training and v001 delivery in 2 days instead of the prior 1-2 week fine-tuning timeline. This is not a production postmortem, an MLCommons submission, or a generalized scaling law for every VFX or DDP workload. [raw](../../raw/crawler/nccl-aws-ml-blog/20260705T041043512489Z-aws-amazon-com-blogs-machine-learning-how-outpost-vfx-uses-aws-to-accelerate-ai-model-trai-f1c01f6e54.md)

The SageMaker AI Blackwell capture is best-practice tuning evidence for distributed training jobs on `ml.p6-b200.48xlarge`, not measured fleet operations. It documents a PyTorch FSDP container path and activation-checkpointing tradeoff: recomputing activations can add compute overhead, but it can free enough GPU memory to raise batch size; the source example shows a 1B-parameter LLM at 8K sequence length where activation checkpointing enables a larger batch and much higher tokens/sec within memory limits. Use it as P6-B200/FSDP/activation-checkpointing planning evidence, not as a production SLO, exact benchmark submission, or catalog-level Blackwell spec row. [raw](../../raw/crawler/nccl-aws-ml-blog/20260626T015712819063Z-aws-amazon-com-blogs-machine-learning-optimize-model-training-on-amazon-sagemaker-ai-with-14a08c4c5d.md)

# NCCL Arxiv Abstract Discovery Leads

The July 12 NCCL arXiv refresh adds bounded abstract-level discovery evidence for collective communication research. Adaptive Space-efficient Collectives describes sparse all-gather, reduce-scatter, and all-reduce algorithms for GPU platforms, backed by a bitvector-based Pici format and adaptive sparse representation changes during the collective. The abstract states speedups over NCCL at 99% input sparsity; keep those as source-stated abstract claims, not reproduced benchmark results, production guidance, or a replacement for NCCL release notes and issue evidence. [raw](../../raw/crawler/nccl-arxiv-papers/20260712T041314410768Z-arxiv-org-abs-2607-04676v1-dadf1c0894.md)

DynamiQ `2602.08923v3` refreshes an existing DynamiQ discovery lead rather than adding a new standalone paper identity. Its v3 abstract keeps the compressed multi-hop all-reduce framing for gradient synchronization, extends PyTorch DDP over NCCL P2P, and states improvement and near-baseline accuracy boundaries. Treat those numbers as abstract discovery evidence only until a later task reads the full paper or obtains benchmark-reproduction evidence. [raw](../../raw/crawler/nccl-arxiv-papers/20260712T041314411159Z-arxiv-org-abs-2602-08923v3-4ed352c0df.md)

# Training Job Controllers

Kubeflow Trainer supplies Kubernetes-native training job abstraction evidence. Its docs organize framework guides for PyTorch, DeepSpeed, Megatron, JAX, XGBoost, and other workloads, plus TrainJob lifecycle and scheduling integration topics. Use it as evidence that distributed training jobs often need a Kubernetes controller layer above framework launchers. [raw](../../raw/links/kubeflow-training-operator-official-docs-20260707.md)

KubeRay is the Ray-on-Kubernetes controller boundary for RayCluster, RayJob, and RayService custom resources. For distributed training, the important split is that Ray Train defines the training/checkpoint API while KubeRay defines the Kubernetes execution and scheduling substrate. [raw](../../raw/links/ray-train-kuberay-official-docs-20260707.md)

# Duplicate Boundaries

This page does not reclassify NCCL communication evidence as complete distributed-training lifecycle evidence. NCCL release notes, issues, and technical blogs remain source-backed coverage for collective communication, SHARP, dynamic communicators, RAS, fabric telemetry, and cost-estimation hooks. [wiki](nccl-technical-blog-network-observability.md)

This page also does not replace inference runtime evidence. vLLM and TensorRT-LLM training/inference bridge signals remain in [Inference Runtime Infrastructure](inference-runtime-infrastructure.md), while this reference keeps to training framework state, launch, checkpoint, and restart mechanics.

# Coverage Use

Use this page as source-backed coverage for:

- `training-distributed`: PyTorch process groups, FSDP sharding, Distributed Checkpoint, `torchrun` restart/elastic semantics, DeepSpeed ZeRO and checkpoint conversion, Megatron-LM project boundaries, Ray Train checkpoint/fault tolerance, and Kubeflow/KubeRay training job controllers.
- `training-distributed`: bounded AWS blog evidence for Outpost VFX DDP-on-P5 case-study results and SageMaker AI P6-B200 FSDP activation-checkpointing tuning tradeoffs.
- `training-distributed`: bounded arXiv abstract discovery evidence for sparse GPU collectives through Adaptive Space-efficient Collectives and a DynamiQ v3 compressed multi-hop all-reduce refresh. These are research leads, not full-paper synthesis or reproduced benchmark coverage.
- `orchestration-scheduling`: only where Kubeflow Trainer and KubeRay explain Kubernetes-native training job execution; use [Orchestration Scheduling Infrastructure](orchestration-scheduling-infrastructure.md) for scheduler, device plugin, GPU operator, Slurm, and quota boundaries.
- `network-storage-cluster`: only where distributed checkpoints depend on durable shared storage; this page does not replace storage/fabric architecture evidence.

Remaining gaps for this layer are production incident/postmortem evidence, measured checkpoint restore benchmarks, framework upgrade failures, and non-PyTorch/DeepSpeed/Ray operational field reports.
The local issue corpora and AWS case-study captures now provide narrow failure examples, case-study measurements, and tuning guidance for collective aborts, version/configuration-sensitive NCCL failures, Ray launch-mode hangs, DDP-on-P5 migration, and FSDP activation-checkpointing. Those examples do not replace production postmortems, checkpoint restore measurements, exact benchmark submissions, or field reports with complete environment and remediation context.

# Citations

- [PyTorch distributed training source note](../../raw/links/pytorch-distributed-training-official-docs-20260707.md)
- [DeepSpeed and Megatron-LM source note](../../raw/links/deepspeed-megatron-training-official-sources-20260707.md)
- [Ray Train and KubeRay source note](../../raw/links/ray-train-kuberay-official-docs-20260707.md)
- [Kubeflow Trainer source note](../../raw/links/kubeflow-training-operator-official-docs-20260707.md)
- [Fault-tolerant NCCL applications raw capture](../../raw/crawler/nccl-technical-blog/20260626T015704295462Z-developer-nvidia-com-blog-building-scalable-and-fault-tolerant-nccl-applications-839bad0938.md)
- [NCCL closed GitHub issues with comments](../../raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-with-comments.json.gz)
- [NCCL issue #2024 crawler supplement](../../raw/crawler/nccl-github-closed-issues/20260703T021318514537Z-github-com-nvidia-nccl-issues-2024-4e07290315.md)
- [SGLang closed issue and PR index](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-index.json)
- [Outpost VFX AWS distributed training case-study capture](../../raw/crawler/nccl-aws-ml-blog/20260705T041043512489Z-aws-amazon-com-blogs-machine-learning-how-outpost-vfx-uses-aws-to-accelerate-ai-model-trai-f1c01f6e54.md)
- [SageMaker AI Blackwell training tuning capture](../../raw/crawler/nccl-aws-ml-blog/20260626T015712819063Z-aws-amazon-com-blogs-machine-learning-optimize-model-training-on-amazon-sagemaker-ai-with-14a08c4c5d.md)
- [NCCL arXiv papers July 12 refresh manifest](../../raw/crawler/nccl-arxiv-papers/manifest-20260712-nccl-arxiv-refresh.json)
- [Adaptive Space-efficient Collectives arXiv abstract capture](../../raw/crawler/nccl-arxiv-papers/20260712T041314410768Z-arxiv-org-abs-2607-04676v1-dadf1c0894.md)
- [DynamiQ v3 arXiv abstract capture](../../raw/crawler/nccl-arxiv-papers/20260712T041314411159Z-arxiv-org-abs-2602-08923v3-4ed352c0df.md)
