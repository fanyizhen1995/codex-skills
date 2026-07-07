---
type: RawSource
title: Triton Inference Server Model Repository And Batcher Documentation
source_kind: web
url: https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/model_repository.html
secondary_urls:
  - https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/batcher.html
captured: 2026-07-07
status: ingested
---
# Source

Official NVIDIA Triton Inference Server documentation:

- https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/model_repository.html
- https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/batcher.html

Captured as a concise source note for `ai_infra` inference-runtime coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- Triton uses a model repository as the serving-time source of models, configuration files, and model versions.
- A typical repository entry has a model-name directory, optional `config.pbtxt`, one or more numeric version subdirectories, and backend-specific model files.
- The repository model supports multiple model versions and allows Triton to load and serve models from the repository according to its configuration.
- Triton supports multiple backend families, including TensorRT, TensorRT-LLM, ONNX Runtime, PyTorch, Python, OpenVINO, FIL, and vLLM backends.
- Triton's scheduler and batcher documentation describes server-side batching as a way to combine individual inference requests for a model.
- Dynamic batching is configured per model and can set preferred batch sizes, maximum queue delay, queue policies, priorities, and queue timeouts.
- The default scheduler dispatches requests to model instances, while the ensemble scheduler composes multiple models and dataflow steps.
- Triton's dynamic batcher is a serving policy surface, not just a client API detail, because the server decides when to form batches from queued requests.

# Use In Wiki

Use this source note for Triton claims about model repository structure, versioned model loading, backend coverage, dynamic batching, scheduler policy, queue controls, and ensemble serving.
