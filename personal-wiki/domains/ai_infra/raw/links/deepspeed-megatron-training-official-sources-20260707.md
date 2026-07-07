---
type: RawSource
title: DeepSpeed And Megatron-LM Distributed Training Sources
source_kind: web
url: https://www.deepspeed.ai/tutorials/zero/
related_urls:
  - https://deepspeed.readthedocs.io/en/latest/model-checkpointing.html
  - https://github.com/NVIDIA/Megatron-LM
captured: 2026-07-07
status: ingested
---
# Source

Official or primary project sources:

- DeepSpeed ZeRO tutorial: https://www.deepspeed.ai/tutorials/zero/
- DeepSpeed model checkpointing documentation: https://deepspeed.readthedocs.io/en/latest/model-checkpointing.html
- NVIDIA Megatron-LM repository: https://github.com/NVIDIA/Megatron-LM

Captured as a concise source note for `ai_infra` distributed training coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official or primary project sources.

# Captured Facts

- DeepSpeed ZeRO is documented as a set of memory optimization techniques for large-model training. It partitions model-training state across distributed hardware rather than treating every data-parallel worker as a full replica.
- ZeRO Stage 1 partitions optimizer state; Stage 2 also partitions gradients; Stage 3 partitions model parameters and gathers/partitions them during forward and backward work.
- ZeRO-Infinity extends ZeRO-3 with offload to CPU and NVMe, so the infrastructure boundary includes accelerator memory, host memory, and storage placement.
- DeepSpeed training configuration exposes ZeRO behavior through JSON configuration such as `zero_optimization` and stage-specific communication or memory knobs.
- DeepSpeed model checkpointing documentation covers saving and loading training checkpoints, recovering fp32 weights from saved ZeRO optimizer state, converting ZeRO checkpoints to consolidated fp32 state dicts, avoiding checkpoint bloat, and Universal Checkpoints.
- Universal Checkpoints are documented as an under-development mechanism for changing the number of GPUs when resuming training that uses data, tensor, or pipeline parallelism.
- The NVIDIA Megatron-LM repository is the primary project source for Megatron large-scale transformer training code, examples, and docs; in this wiki it should be used as project-level evidence for tensor/pipeline/data-parallel training boundaries, not as a source for DeepSpeed-specific ZeRO internals unless cited through DeepSpeed's Megatron integration material.

# Use In Wiki

Use this source note for DeepSpeed ZeRO sharding, ZeRO checkpoint conversion, offload boundaries, Universal Checkpoint caveats, and Megatron-LM as a primary project source for large-scale transformer training infrastructure. Keep model-quality claims out of scope unless they directly explain infrastructure behavior.
