---
type: RawSource
title: Ray Train And KubeRay Documentation
source_kind: web
url: https://docs.ray.io/en/latest/train/train.html
related_urls:
  - https://docs.ray.io/en/latest/train/user-guides/checkpoints.html
  - https://docs.ray.io/en/latest/train/user-guides/fault-tolerance.html
  - https://docs.ray.io/en/latest/cluster/kubernetes/index.html
captured: 2026-07-07
status: ingested
---
# Source

Official Ray documentation:

- Ray Train: https://docs.ray.io/en/latest/train/train.html
- Ray Train checkpoints: https://docs.ray.io/en/latest/train/user-guides/checkpoints.html
- Ray Train fault tolerance: https://docs.ray.io/en/latest/train/user-guides/fault-tolerance.html
- Ray on Kubernetes / KubeRay: https://docs.ray.io/en/latest/cluster/kubernetes/index.html

Captured as a concise source note for `ai_infra` distributed training and orchestration coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- Ray Train is the Ray library for distributed model training and exposes trainer abstractions such as TorchTrainer, scaling configuration, run configuration, and checkpoint reporting.
- Ray Train checkpoints are reported from workers and restored through `ray.train.get_checkpoint()` so a restarted worker can recover training state from the latest checkpoint.
- Ray Train fault tolerance uses `FailureConfig(max_failures=...)` and can restart worker groups after worker or node failures when a checkpoint and storage path are configured.
- For multi-node training, Ray recommends configuring a shared storage path such as cloud object storage or NFS so worker checkpoints survive node loss and can be downloaded by replacement workers.
- Ray driver fault tolerance depends on relaunching with the same run name and storage path so the driver can find the previous run state and latest reported checkpoints.
- KubeRay introduces Kubernetes custom resources for RayCluster, RayJob, and RayService to manage Ray clusters and workload modes on Kubernetes.
- KubeRay documentation includes operator concerns such as RayCluster configuration, autoscaling, label-based scheduling, Kueue integration, Volcano integration, GPU use, distributed checkpointing examples, observability, and troubleshooting.

# Use In Wiki

Use this source note for Ray Train distributed training jobs, checkpoint/resume semantics, worker and driver fault tolerance, RayJob/RayCluster Kubernetes execution, KubeRay scheduling integrations, autoscaling, and GPU/Kubernetes boundaries. Do not use it as evidence that every Ray deployment is production-ready without separate operational evidence.
