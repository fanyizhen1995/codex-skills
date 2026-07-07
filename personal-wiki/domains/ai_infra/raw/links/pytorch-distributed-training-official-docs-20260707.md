---
type: RawSource
title: PyTorch Distributed Training Documentation
source_kind: web
url: https://docs.pytorch.org/docs/stable/distributed.html
related_urls:
  - https://docs.pytorch.org/docs/stable/fsdp.html
  - https://docs.pytorch.org/docs/stable/distributed.checkpoint.html
  - https://docs.pytorch.org/docs/stable/elastic/run.html
captured: 2026-07-07
status: ingested
---
# Source

Official PyTorch documentation:

- Distributed communication package: https://docs.pytorch.org/docs/stable/distributed.html
- FullyShardedDataParallel: https://docs.pytorch.org/docs/stable/fsdp.html
- Distributed Checkpoint: https://docs.pytorch.org/docs/stable/distributed.checkpoint.html
- torchrun elastic launch: https://docs.pytorch.org/docs/stable/elastic/run.html

Captured as a concise source note for `ai_infra` distributed training coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- `torch.distributed` is PyTorch's distributed communication package and documents built-in communication backends such as Gloo, MPI, NCCL, and XCCL with different CPU/GPU capability boundaries.
- PyTorch distributed process groups expose initialization, backend availability, point-to-point communication, collectives, monitored barriers, and distributed error classes. This is broader than NCCL alone because it defines the framework-level distributed runtime boundary.
- `torchrun` is the elastic launch entry point for `torch.distributed.run` and can launch single-node, fixed-size multi-node, fault-tolerant, and elastic worker groups.
- For fixed-size fault tolerance and elastic runs, `torchrun` uses rendezvous metadata such as rendezvous id, backend, endpoint, node counts, process count per node, and maximum restarts.
- PyTorch documents that worker failures or membership changes kill surviving workers and restart a new worker group, which means training scripts must checkpoint progress and avoid stable-rank/world-size assumptions.
- FullyShardedDataParallel (FSDP) wraps a module and shards module parameters across data-parallel workers. Its sharding strategies can shard parameters, gradients, and optimizer states, with all-gather and reduce-scatter during forward and backward computation.
- FSDP state-dict configuration covers full, sharded, local, and optimizer state dicts, including rank-0-only and offload-to-CPU options for checkpoint memory behavior.
- `torch.distributed.checkpoint` supports parallel save and load from multiple ranks, emits multiple files per checkpoint, and handles load-time resharding so a checkpoint can be saved under one topology and loaded under another.

# Use In Wiki

Use this source note for framework-level distributed training, FSDP sharding, PyTorch distributed checkpointing, elastic launch, worker restart, and checkpoint/resume boundaries. Do not use it as a replacement for NCCL communication evidence or for production incident evidence.
