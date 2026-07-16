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
  - ../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-index.json
  - ../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-with-comments.json.gz
  - ../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-summary.json
  - ../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-summary.json
  - ../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-index.json
  - ../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-with-comments.json.gz
  - ../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-index.json
  - ../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-with-comments.json.gz
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-index.json
  - ../../raw/crawler/nccl-aws-ml-blog/manifest-20260712-hyperpod-dpd.json
  - ../../raw/crawler/nccl-aws-ml-blog/20260712T041317574335Z-aws-amazon-com-blogs-machine-learning-disaggregated-prefill-and-decode-for-llm-inference-o-0ba0cabe09.md
updated: 2026-07-16
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

# HyperPod Inference Operator DPD Boundary

The SageMaker HyperPod DPD capture adds a provider-specific inference-operator boundary. It states that DPD requires HyperPod Inference Operator version 3.2 or later and is activated on an `InferenceEndpointConfig` by adding `spec.pdSpec`. The presence of `pdSpec` makes the endpoint disaggregated: the operator creates separate prefill and decode `Deployment` objects and wires them together through the router and LMCache PD backend. [manifest](../../raw/crawler/nccl-aws-ml-blog/manifest-20260712-hyperpod-dpd.json) [raw](../../raw/crawler/nccl-aws-ml-blog/20260712T041317574335Z-aws-amazon-com-blogs-machine-learning-disaggregated-prefill-and-decode-for-llm-inference-o-0ba0cabe09.md)

The source scopes the DPD manifest semantics. `pdSpec.replicas` scales prefill and decode roles independently, `pdSpec.resources` applies per role, top-level `worker.resources` is ignored for DPD pods, `routingThreshold` decides when a prompt uses the disaggregated path, and per-role `args` override or append role-specific vLLM flags. `spec.worker.environmentVariables` is shared by prefiller and decoder containers, so per-role behavior belongs in `pdSpec.{prefillSpec,decodingSpec}.args`. This is an operator/API contract for this HyperPod source, not general Kubernetes scheduling behavior. [raw](../../raw/crawler/nccl-aws-ml-blog/20260712T041317574335Z-aws-amazon-com-blogs-machine-learning-disaggregated-prefill-and-decode-for-llm-inference-o-0ba0cabe09.md)

The runtime deployment shape is also source-scoped. The blog says applying the manifest creates prefill and decode pods in the workload namespace and a router deployment in `hyperpod-inference-system`; each model pod has a vLLM worker, Nginx reverse proxy, and OpenTelemetry collector, while the router pod has router and OpenTelemetry containers. Readiness is exposed through the `InferenceEndpointConfig` condition. This is useful orchestration evidence for HyperPod DPD pod composition, but it is not a production incident, rollout guarantee, KServe coverage, or autoscaling proof. [raw](../../raw/crawler/nccl-aws-ml-blog/20260712T041317574335Z-aws-amazon-com-blogs-machine-learning-disaggregated-prefill-and-decode-for-llm-inference-o-0ba0cabe09.md)

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

# Local Scheduling Issue Signals

Kueue issues add concrete admission and queueing failure modes beyond the design documents. Issue #1726 reports a job whose workload was admitted but never unsuspended. Issue #696 explicitly discusses ResourceQuota admission interaction and names potential deadlocks or unschedulable pending pods as the operational risk. Issue #6143 reports serialized pod preemption causing significant delays before a ClusterQueue can reclaim nominal quota. These records support treating Kueue admission as a runtime state machine with failure and latency modes, not just a static quota model. [raw](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-with-comments.json.gz)

Kueue issue #1407 ties ResourceFlavor placement to Kubeflow PyTorchJobs: node labels from the flavor were not added as pod node selectors, so accelerator placement metadata did not reach the training pods as expected. Issue #3094 shows MultiKueue AdmissionCheck conditions becoming confusing during investigations, and issues #2867 and #2941 show extended-resource and DRA concerns entering Kueue quota management. These are issue-level signals for accelerator placement and admission debugging; use official Kueue docs for the intended API semantics. [raw](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-index.json)

Volcano issues add a second operational slice for gang scheduling, preemption, and GPU device integration. Issue #452 reports an MPIJob with gang scheduling becoming unschedulable with `NotEnoughResources` even though the reporter believed enough GPU resources existed. Issues #2547 and #3329 report high-priority GPU workloads not preempting lower-priority work under preempt/reclaim configurations. Issue #2701 reports GPU sharing allocation failing with a missing GPU id, while #3384 reports a vGPU memory limit not being reflected inside a container. [raw](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-with-comments.json.gz)

Volcano also supplies upgrade and scheduler-health examples. Issue #3301 reports scheduler panics around insufficient resource operations, #2416 reports gang-scheduled tasks staying unschedulable after installing a newer chart/source tree, and #2379 reports a GKE upgrade from Volcano 1.5 to 1.6 failing because components requested reserved priority-class quota. These examples fill local operator and scheduler failure evidence, but they are not production postmortems with service-impact timelines. [raw](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-index.json)

Parent-5 adds a bounded DRA and device-plugin scheduling slice from local issue records that were not already promoted. Kubernetes issue #139016 reports pods getting stuck when DRA scheduling combines a shared multi-node `ResourceSlice` or `ResourceClaim` with per-node GPU claims. Issue #137617 reports repeated `FailedScheduling` for gang scheduling with a shared ResourceClaim, with preemption not helping. Issue #138882 reports a kube-scheduler panic when a DRA `allocationMode: All` request matches a device consuming counters from a pool with shared counters, and issue #135661 reports a DynamicResources CEL selector runtime error when a device lacks the expected `gpu.nvidia.com` nested attribute. These are issue-level scheduler and DRA-plugin signals, not scheduler benchmark results. [raw](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-with-comments.json.gz)

The same local Kubernetes slice adds device-plugin transition signals. Issue #133702 reports kubelet `unhealthyDevices` and endpoint state getting out of sync after a DRA extended-resource plus ResourceClaim e2e test. Issue #133488 reports the DRA extended-resource device-plugin test leaving an extended resource in node `Allocatable` or `Capacity` after plugin cleanup. Issue #135901 reports kubelet failing container creation when a second pod adds another ResourceClaim after one claim is already prepared, and issue #138407 reports `pod.status.resourceClaimStatuses` flapping for a pending pod using ResourceClaimTemplates. Treat these as kubelet/device-management issue signals around DRA and legacy device-plugin coexistence. [raw](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-with-comments.json.gz)

Kueue issue #12207 adds quota-admission evidence for DRA partitionable devices: mixed ClusterQueue units for `gpu.memory` allowed a device-count-style queue to borrow far more memory than intended from a counter-based queue, with the issue environment naming OpenShift, Kueue Operator, NVIDIA GPU Operator, a DRA driver, and the `DRAPartitionableDevices` feature gate. Kueue issue #9868 is kept as a feature-boundary record for DRA extended resources bridging legacy `nvidia.com/gpu` requests to ResourceClaims; it is not counted as a failure by itself. [raw](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-with-comments.json.gz)

Volcano issue #5119 reports a `vcjob` using `ResourceClaimTemplate` failing dynamic-resource preparation when the pod skipped DRA scheduler-plugin operations. Issue #4692 reports Volcano's DRA PreBind integration blocking the main scheduling workflow when a lock is not released until timeout. Issue #5335 reports dry-run rollback leaving vGPU assignment annotations that bypass later capacity validation and can over-subscribe GPUs, and issue #5361 reports Hami vGPU scheduling taking more than ten minutes on a 200-node, 8-GPU-per-node cluster after a Volcano and device-plugin upgrade because API-server rate limiting delayed resource-view generation. Older issue #2965 remains a device-plugin reinstall boundary: node `OutOfSync` marking prevented scheduling after GPU resource reporting dropped to zero. These stay issue-level operational signals, not GPU-operator upgrade postmortems with full service impact and remediation ownership. [raw](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-with-comments.json.gz)

Parent-20 adds a bounded Volcano scheduler benchmark and performance slice from the same local corpus. Volcano issue #999 is a benchmark-design request rather than a measured result: it asks for scalability performance testing, suggests Kubemark to simulate nodes, names large pod counts such as 100k pods on 1k-5k nodes, and separates scheduler throughput from average scheduling latency under fixed pod creation frequency. A comment adds that scheduler performance needs a pressure simulator because RPC response latency does not directly represent scheduling work. [raw](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-with-comments.json.gz)

Volcano issue #1740 is a throughput requirement signal for high-performance workload submission. The issue states that high-performance workloads are moving to Kubernetes and that current scheduler throughput did not meet large-scale job-submission requirements; a maintainer comment asks for a performance report before more improvement. Treat it as demand and design pressure for throughput work, not as a throughput benchmark result. [raw](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-with-comments.json.gz)

Volcano issue #1059 is a reporter-stated performance incident with an environment boundary: Volcano v1.0.1 on Kubernetes 1.14 reportedly took nearly 30 minutes to schedule 1k podgroups with 1w pods in a 1w-node cluster, and 2 MB/s log growth at log level 3 was reported as dramatically affecting scheduler performance. This supports log-volume sensitivity as issue-level scheduler performance evidence, not a controlled benchmark baseline or production postmortem. [raw](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-with-comments.json.gz)

Volcano issue #5536 adds recent scheduler hot-path optimization evidence: after #5505, stable-filter plugins such as `NodeAffinity` can have `PreFilter` return `Skip`, but `predicateByStablefilter` still called `Filter()` for every node unless it checked `handleSkipPredicatePlugin(state, name)`. This supports stable-filter skip handling as a scheduler hot-path concern; it does not provide measured throughput or latency output. [raw](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-with-comments.json.gz)

The SGLang index remains a downstream runtime lead for Slurm and accelerator scheduling. In particular, issue #23627 records DP scheduler workers escaping a Slurm job cgroup and surviving job termination, blocking GPU reuse. This is useful evidence that runtime-level schedulers can violate HPC allocation cleanup boundaries, but it should be paired with Slurm or runtime-specific source captures before becoming a general Slurm-on-Kubernetes or Slurm operations claim. [raw](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-index.json)

# Duplicate Boundaries

This page does not duplicate [Security Governance Cost Infrastructure](security-governance-cost-infrastructure.md). That page covers quota governance, tenant isolation, cost attribution, and capacity planning. This page uses Kueue and ResourceQuota only to explain scheduler admission and accelerator placement boundaries.

This page does not replace [Distributed Training Infrastructure](distributed-training-infrastructure.md). PyTorch, DeepSpeed, Ray Train, and Kubeflow sources explain framework and TrainJob behavior there; this page focuses on schedulers, device exposure, operators, and Kubernetes/HPC execution surfaces.

# Coverage Use

Use this page as source-backed coverage for:

- `orchestration-scheduling`: Ray/KubeRay CRDs, RayJob/RayCluster execution, Slurm GPU/GRES scheduling, Kubernetes device plugins, NVIDIA and AMD GPU operators, Kubeflow Trainer job controllers, quota/admission interactions with Kueue and ResourceQuota, and SageMaker HyperPod Inference Operator DPD boundaries for `InferenceEndpointConfig.spec.pdSpec`, prefill/decode/router Deployments, role-specific replicas/resources/args, shared worker environment variables, and pod/container readiness surfaces.
- `training-distributed`: only where KubeRay and Kubeflow explain training job controllers above framework runtimes.
- `security-governance-cost`: only where Kueue quota, ResourceFlavor, cohorts, or ResourceQuota explain admission and accelerator governance; use the security/governance page for cost and tenant isolation.
- `hardware-accelerator`: only where device plugins and GPU operators expose or manage accelerators; do not use this page for SKU parameters.

Remaining gaps for this layer are production scheduling incidents, cross-scheduler migration reports, Slurm-on-Kubernetes bridge deployments, controlled scheduler benchmark results, and operator upgrade failure/postmortem evidence.
The local issue corpora now cover issue-level admission, preemption, DRA ResourceClaim/ResourceSlice, GPU device, device-plugin coexistence, vGPU, scheduler benchmark design, throughput demand, log-volume performance sensitivity, stable-filter skip handling, and upgrade-adjacent failure signals. They do not yet close the need for production incidents, controlled scheduler benchmark outputs with full environment and measured results, Slurm-on-Kubernetes bridge deployments, or GPU-operator/device-plugin upgrade postmortems with full environment and remediation context.

# Citations

- [Ray Train and KubeRay source note](../../raw/links/ray-train-kuberay-official-docs-20260707.md)
- [Slurm GPU and GRES scheduling source note](../../raw/links/slurm-gpu-scheduling-official-docs-20260707.md)
- [Kubernetes device plugin and GPU operators source note](../../raw/links/kubernetes-device-plugin-gpu-operators-official-docs-20260707.md)
- [Kubeflow Trainer source note](../../raw/links/kubeflow-training-operator-official-docs-20260707.md)
- [Kubernetes and Kueue quota governance source note](../../raw/links/kubernetes-kueue-quota-governance-official-20260707.md)
- [Kubernetes closed issues summary](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-summary.json)
- [Kubernetes closed issues index](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-index.json)
- [Volcano closed issues summary](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-summary.json)
- [Kueue closed issues summary](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-summary.json)
- [Kubernetes joined issues and comments](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-with-comments.json.gz)
- [Volcano closed issues with comments](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-with-comments.json.gz)
- [Kueue closed issues with comments](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-with-comments.json.gz)
- [SGLang closed issue and PR index](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-index.json)
- [SageMaker HyperPod DPD manifest](../../raw/crawler/nccl-aws-ml-blog/manifest-20260712-hyperpod-dpd.json)
- [SageMaker HyperPod DPD AWS ML Blog capture](../../raw/crawler/nccl-aws-ml-blog/20260712T041317574335Z-aws-amazon-com-blogs-machine-learning-disaggregated-prefill-and-decode-for-llm-inference-o-0ba0cabe09.md)
