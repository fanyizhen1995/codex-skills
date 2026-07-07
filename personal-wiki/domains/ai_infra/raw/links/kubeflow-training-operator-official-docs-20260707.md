---
type: RawSource
title: Kubeflow Trainer And Training Operator Documentation
source_kind: web
url: https://www.kubeflow.org/docs/components/trainer/
related_urls:
  - https://www.kubeflow.org/docs/components/trainer/user-guides/
  - https://www.kubeflow.org/docs/components/trainer/operator-guides/job-scheduling/
  - https://www.kubeflow.org/docs/components/training/user-guides/mpi/
captured: 2026-07-07
status: ingested
---
# Source

Official Kubeflow documentation:

- Kubeflow Trainer: https://www.kubeflow.org/docs/components/trainer/
- Trainer user guides: https://www.kubeflow.org/docs/components/trainer/user-guides/
- Trainer job scheduling: https://www.kubeflow.org/docs/components/trainer/operator-guides/job-scheduling/
- Legacy MPI training guide: https://www.kubeflow.org/docs/components/training/user-guides/mpi/

Captured as a concise source note for `ai_infra` Kubernetes-native training job coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official source navigation and component documentation.

# Captured Facts

- Kubeflow Trainer is the current Kubeflow component area for running distributed training workloads on Kubernetes, with user guides for PyTorch, DeepSpeed, Megatron, JAX, XGBoost, Flux, MLX, distributed data cache, TrainJob lifecycle, and local execution.
- Kubeflow Trainer operator guides include runtime, ML policy, job template, runtime patches, extension framework, and job scheduling topics.
- Kubeflow Trainer job scheduling documentation links scheduling integrations such as coscheduling, Volcano, Kueue, and KAI Scheduler.
- The Kubeflow docs preserve a legacy Kubeflow Training Operator area with workload-specific guides such as PyTorchJob, TFJob, PaddleJob, XGBoostJob, JAXJob, job scheduling, MPIJob, and Prometheus monitoring.
- In this wiki, Kubeflow should be treated as Kubernetes-native training job abstraction evidence. It does not replace lower-level framework sources such as PyTorch, DeepSpeed, Ray Train, or Slurm scheduler evidence.

# Use In Wiki

Use this source note for Kubernetes TrainJob lifecycle, framework-specific training job abstractions, scheduling integrations, and the boundary between ML framework launchers and Kubernetes batch/job controllers.
