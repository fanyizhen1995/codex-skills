---
type: RawSource
title: Network Storage Topology And Benchmark Official Sources
source_kind: web
url: https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod.html
related_urls:
  - https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-slurm.html
  - https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-resiliency-slurm.html
  - https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-topology.html
  - https://mlcommons.org/benchmarks/storage/
  - https://github.com/mlcommons/storage
  - https://github.com/mlcommons/storage_results_v2.0
captured: 2026-07-07
status: ingested
---
# Source

Official and primary sources used for bounded network/storage topology and benchmark coverage:

- Amazon SageMaker HyperPod overview: https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod.html
- Amazon SageMaker HyperPod Slurm orchestrator documentation: https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-slurm.html
- Amazon SageMaker HyperPod cluster resiliency with Slurm: https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-resiliency-slurm.html
- Amazon SageMaker HyperPod topology documentation: https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-topology.html
- MLCommons Storage benchmark landing page: https://mlcommons.org/benchmarks/storage/
- MLCommons Storage benchmark repository: https://github.com/mlcommons/storage
- MLCommons Storage benchmark v2.0 results repository: https://github.com/mlcommons/storage_results_v2.0

Captured as concise source notes for `ai_infra` network-storage-cluster coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the cited sources.

# Link Probe

- `web.open` returned the AWS HyperPod overview and Slurm documentation on 2026-07-07.
- `web.open` returned the MLCommons Storage benchmark landing page, benchmark repository, and v2.0 results repository on 2026-07-07.
- Local sandbox `urllib` HEAD probes for the same URLs returned `Temporary failure in name resolution`. Treat local network status as blocked and web-open source access as the successful content probe for this run.

# Captured Facts

## AWS HyperPod topology and checkpoint data path

- SageMaker HyperPod is AWS primary evidence for managed AI training clusters that combine accelerator instances with health monitoring, resiliency workflows, and optional Slurm orchestration.
- HyperPod with Slurm supports multiple instance groups, including controller and worker groups, and the documentation records optional choices for Elastic Fabric Adapter and FSx for Lustre file systems in the cluster configuration path.
- The HyperPod documentation exposes topology-aware placement for reducing training job launch time on supported clustered instance topologies, including Slurm-side topology plugin behavior for hierarchical or block placement. Use this as topology-control evidence only; it does not prove a specific workload benchmark.
- HyperPod Slurm resiliency documentation ties node replacement and job resume behavior to checkpoint-aware training jobs. It supports the narrow claim that checkpoint location and resume policy are part of the training data path, not only the model framework.
- The HyperPod resiliency material includes EFA health-check integration in the Slurm node-replacement workflow. Use this as AWS non-NVIDIA fabric-operations evidence, with the boundary that it is managed-service operations documentation rather than a public incident report.

## MLCommons Storage benchmark mechanics and result boundaries

- MLCommons Storage is a primary benchmark source for AI storage. The benchmark is designed around AI training storage patterns and reports metadata such as submitter, system type, storage system, benchmark version, workload, backend, number of compute nodes, accelerator count, networking, and throughput.
- The MLCommons Storage benchmark repository documents benchmark execution around workloads such as UNet3D, ResNet50, CosmoFlow, and checkpointing, and includes POSIX and object backend support.
- Treat MLCommons Storage as benchmark-method and result-format evidence. Do not turn a results-table entry into a general product performance claim unless the exact submission, storage configuration, hardware/cloud environment, networking, workload, and measured throughput are cited directly.
- The MLCommons v2.0 results repository is the source boundary for measured results. This note does not select or rank individual vendors; it only preserves the benchmark framework and where result artifacts live.

# Use In Wiki

Use this source note for source-backed claims about:

- AWS HyperPod topology-aware scheduling and managed AI cluster topology controls;
- EFA health-check and node replacement as AWS fabric-operation evidence;
- FSx for Lustre as a HyperPod cluster file-system option when paired with the existing FSx source note;
- checkpoint-aware resume as a training data-path boundary;
- MLCommons Storage as AI storage benchmark method/result-framework evidence.

Do not use this note to claim full production incident coverage, universal storage performance, or product-specific benchmark leadership.
