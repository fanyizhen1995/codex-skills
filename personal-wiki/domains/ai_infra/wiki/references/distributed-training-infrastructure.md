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
updated: 2026-07-07
related:
  - ai-infra-coverage-map.md
  - nccl-technical-blog-network-observability.md
  - orchestration-scheduling-infrastructure.md
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

# Training Job Controllers

Kubeflow Trainer supplies Kubernetes-native training job abstraction evidence. Its docs organize framework guides for PyTorch, DeepSpeed, Megatron, JAX, XGBoost, and other workloads, plus TrainJob lifecycle and scheduling integration topics. Use it as evidence that distributed training jobs often need a Kubernetes controller layer above framework launchers. [raw](../../raw/links/kubeflow-training-operator-official-docs-20260707.md)

KubeRay is the Ray-on-Kubernetes controller boundary for RayCluster, RayJob, and RayService custom resources. For distributed training, the important split is that Ray Train defines the training/checkpoint API while KubeRay defines the Kubernetes execution and scheduling substrate. [raw](../../raw/links/ray-train-kuberay-official-docs-20260707.md)

# Duplicate Boundaries

This page does not reclassify NCCL communication evidence as complete distributed-training lifecycle evidence. NCCL release notes, issues, and technical blogs remain source-backed coverage for collective communication, SHARP, dynamic communicators, RAS, fabric telemetry, and cost-estimation hooks. [wiki](nccl-technical-blog-network-observability.md)

This page also does not replace inference runtime evidence. vLLM and TensorRT-LLM training/inference bridge signals remain in [Inference Runtime Infrastructure](inference-runtime-infrastructure.md), while this reference keeps to training framework state, launch, checkpoint, and restart mechanics.

# Coverage Use

Use this page as source-backed coverage for:

- `training-distributed`: PyTorch process groups, FSDP sharding, Distributed Checkpoint, `torchrun` restart/elastic semantics, DeepSpeed ZeRO and checkpoint conversion, Megatron-LM project boundaries, Ray Train checkpoint/fault tolerance, and Kubeflow/KubeRay training job controllers.
- `orchestration-scheduling`: only where Kubeflow Trainer and KubeRay explain Kubernetes-native training job execution; use [Orchestration Scheduling Infrastructure](orchestration-scheduling-infrastructure.md) for scheduler, device plugin, GPU operator, Slurm, and quota boundaries.
- `network-storage-cluster`: only where distributed checkpoints depend on durable shared storage; this page does not replace storage/fabric architecture evidence.

Remaining gaps for this layer are production incident/postmortem evidence, measured checkpoint restore benchmarks, framework upgrade failures, and non-PyTorch/DeepSpeed/Ray operational field reports.

# Citations

- [PyTorch distributed training source note](../../raw/links/pytorch-distributed-training-official-docs-20260707.md)
- [DeepSpeed and Megatron-LM source note](../../raw/links/deepspeed-megatron-training-official-sources-20260707.md)
- [Ray Train and KubeRay source note](../../raw/links/ray-train-kuberay-official-docs-20260707.md)
- [Kubeflow Trainer source note](../../raw/links/kubeflow-training-operator-official-docs-20260707.md)
- [Fault-tolerant NCCL applications raw capture](../../raw/crawler/nccl-technical-blog/20260626T015704295462Z-developer-nvidia-com-blog-building-scalable-and-fault-tolerant-nccl-applications-839bad0938.md)
