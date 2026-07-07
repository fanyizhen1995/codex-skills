---
type: Reference
title: Inference Runtime Infrastructure
description: Source-backed reference for inference serving runtime mechanics across vLLM, TensorRT-LLM, Triton Inference Server, llama.cpp, ONNX Runtime GenAI, and local TensorRT/vLLM captures.
domain: ai_infra
status: reviewed
aliases:
  - inference runtime infrastructure
  - LLM serving runtime infrastructure
  - model serving runtime systems
tags:
  - inference-runtime
  - serving
  - kv-cache
  - batching
  - model-runtime
source_refs:
  - ../../raw/links/vllm-readme-official-20260707.md
  - ../../raw/crawler/nccl-vllm-blog/20260626T015715356602Z-vllm-ai-blog-2026-05-28-native-rl-apis-87d0cc671e.md
  - ../../raw/crawler/nccl-vllm-blog/20260626T015715357250Z-vllm-ai-blog-2026-05-18-pegaflow-c7d76fc4e2.md
  - ../../raw/links/tensorrt-llm-kv-cache-official-docs-20260707.md
  - ../../raw/crawler/nccl-technical-blog/20260626T015704292802Z-developer-nvidia-com-blog-scaling-ai-inference-across-multiple-gpus-using-nvidia-tensorrt-6fabda0844.md
  - ../../raw/links/triton-inference-server-batcher-official-docs-20260707.md
  - ../../raw/links/llama-cpp-server-official-docs-20260707.md
  - ../../raw/links/onnx-runtime-genai-config-official-docs-20260707.md
updated: 2026-07-07
related:
  - ai-infra-coverage-map.md
  - ../projects/sglang.md
  - ../concepts/nvidia-green-context.md
---
# Summary

This reference broadens the `inference-runtime` layer beyond the existing SGLang and CUDA Green Context pages. It uses concise official source notes for vLLM, TensorRT-LLM, Triton Inference Server, llama.cpp, and ONNX Runtime GenAI, plus existing local vLLM and NVIDIA TensorRT captures that were already in raw evidence.

The common boundary is serving-time infrastructure: request scheduling and batching, KV-cache lifetime, model repository or config loading, hardware/provider selection, distributed execution knobs, and API-server surfaces. Model quality, prompt design, and application UX stay outside this page unless they directly affect runtime behavior.

# Runtime Surfaces

The sources split inference runtime into several repeated control surfaces:

- `request admission and batching`: vLLM continuous batching and chunked prefill, Triton dynamic batching, and TensorRT-LLM in-flight batching metrics all treat the server as an active scheduler rather than a passive wrapper. [raw](../../raw/links/vllm-readme-official-20260707.md) [raw](../../raw/links/triton-inference-server-batcher-official-docs-20260707.md) [raw](../../raw/links/tensorrt-llm-kv-cache-official-docs-20260707.md)
- `KV-cache lifecycle`: vLLM PagedAttention and prefix caching, TensorRT-LLM block reuse and offload, vLLM PegaFlow's external cache process, and ONNX Runtime GenAI's past/present KV names show that generated-token state is a first-class runtime asset. [raw](../../raw/links/vllm-readme-official-20260707.md) [raw](../../raw/crawler/nccl-vllm-blog/20260626T015715357250Z-vllm-ai-blog-2026-05-18-pegaflow-c7d76fc4e2.md) [raw](../../raw/links/tensorrt-llm-kv-cache-official-docs-20260707.md) [raw](../../raw/links/onnx-runtime-genai-config-official-docs-20260707.md)
- `model loading and execution target`: Triton uses a model repository with versioned model directories; ONNX Runtime GenAI uses `genai_config.json`; llama.cpp uses local/GGUF-style model loading; TensorRT and TensorRT-LLM use optimized runtime engines and serve commands. [raw](../../raw/links/triton-inference-server-batcher-official-docs-20260707.md) [raw](../../raw/links/onnx-runtime-genai-config-official-docs-20260707.md) [raw](../../raw/links/llama-cpp-server-official-docs-20260707.md) [raw](../../raw/links/tensorrt-llm-kv-cache-official-docs-20260707.md)
- `parallel and hardware placement`: vLLM exposes tensor, pipeline, data, expert, and context parallelism; TensorRT-LLM exposes tensor, pipeline, and expert parallel knobs in serving; TensorRT 11.0 adds multi-device inference with NCCL collectives; ONNX Runtime GenAI selects execution providers; llama.cpp spans local CPU/GPU backends. [raw](../../raw/links/vllm-readme-official-20260707.md) [raw](../../raw/links/tensorrt-llm-kv-cache-official-docs-20260707.md) [raw](../../raw/crawler/nccl-technical-blog/20260626T015704292802Z-developer-nvidia-com-blog-scaling-ai-inference-across-multiple-gpus-using-nvidia-tensorrt-6fabda0844.md) [raw](../../raw/links/onnx-runtime-genai-config-official-docs-20260707.md) [raw](../../raw/links/llama-cpp-server-official-docs-20260707.md)

# vLLM

vLLM is the broad serving engine in this source set. Its README lists PagedAttention for KV-cache memory management, continuous batching, chunked prefill, prefix caching, OpenAI-compatible serving, structured outputs, speculative decoding, streaming, optimized attention/kernel integrations, multiple parallelism modes, and disaggregated serving features. These are infrastructure claims because they determine how requests share memory, scheduling, and hardware. [raw](../../raw/links/vllm-readme-official-20260707.md)

The existing local vLLM blogs add two operational details that the README alone does not cover. The native RL API capture describes weight syncing between training and inference workers, with initialization/start/update/finish phases and NCCL or CUDA IPC transfer backends. That is runtime infrastructure for online RL because the serving engine must safely accept new weights without each RL framework carrying bespoke worker extensions. [raw](../../raw/crawler/nccl-vllm-blog/20260626T015715356602Z-vllm-ai-blog-2026-05-28-native-rl-apis-87d0cc671e.md)

The PegaFlow capture frames KV cache as a long-lived serving asset rather than state tied only to one engine process. It moves cache ownership into a standalone process, connects local vLLM workers through CUDA IPC and gRPC, can use RDMA for remote block reads, and adds SSD as a colder cache tier. Use this as evidence for external KV-cache service boundaries, not as a universal performance claim outside the documented setup. [raw](../../raw/crawler/nccl-vllm-blog/20260626T015715357250Z-vllm-ai-blog-2026-05-18-pegaflow-c7d76fc4e2.md)

# TensorRT And TensorRT-LLM

TensorRT-LLM provides the LLM-serving view of NVIDIA's optimized runtime stack. Its KV-cache documentation describes block-based cache storage, cross-request block reuse through radix lookup, priority eviction, host offload, and configurable memory/token limits through `KvCacheConfig`. Its serving command starts an OpenAI-compatible server with model, host, port, tensor parallelism, pipeline parallelism, expert parallelism, backend, metrics, health, version, completions, and chat-completions surfaces. [raw](../../raw/links/tensorrt-llm-kv-cache-official-docs-20260707.md)

The local NVIDIA TensorRT blog covers a lower-level multi-device inference boundary. TensorRT 11.0 adds distributed collective layers and uses NCCL collectives for multi-GPU inference, with tensor parallelism and context parallelism as separate strategies. The source discusses AllGather KV, Ring Attention, and DeepSpeed Ulysses as context-parallel approaches for long-sequence attention workloads. This is TensorRT runtime evidence, while TensorRT-LLM is the LLM serving/runtime layer above it. [raw](../../raw/crawler/nccl-technical-blog/20260626T015704292802Z-developer-nvidia-com-blog-scaling-ai-inference-across-multiple-gpus-using-nvidia-tensorrt-6fabda0844.md)

# Triton Inference Server

Triton is the multi-backend serving control plane in this group. Its model repository documentation makes model location, versioning, and `config.pbtxt` part of the runtime contract. The repository can hold multiple model versions and model files for backend-specific runtimes, while Triton supports backends that include TensorRT, TensorRT-LLM, ONNX Runtime, PyTorch, Python, OpenVINO, FIL, and vLLM. [raw](../../raw/links/triton-inference-server-batcher-official-docs-20260707.md)

Triton's dynamic batching and scheduler documentation is the clearest non-LLM-specific batching source in this round. Dynamic batching is configured per model and can set preferred batch sizes, maximum queue delay, queue policies, priorities, and timeouts. That means Triton should be treated as a serving scheduler and backend router, not merely as an HTTP endpoint around model files. [raw](../../raw/links/triton-inference-server-batcher-official-docs-20260707.md)

# llama.cpp

llama.cpp belongs in the layer as local inference runtime evidence. Its README emphasizes C/C++ inference with minimal setup, local and cloud use, GGUF model loading, `llama-cli` for local generation, and `llama-server` for OpenAI-compatible serving. It also documents a wide backend range across CPU, Apple silicon, CUDA, HIP, Vulkan, SYCL, MUSA, CANN, OpenCL, and hybrid CPU/GPU execution. [raw](../../raw/links/llama-cpp-server-official-docs-20260707.md)

This page should not overextend llama.cpp into fleet-scale serving claims. The source supports local/runtime deployment, quantization, and server mode; it does not replace Triton or vLLM evidence for multi-model repository management, centralized scheduling, or distributed serving control planes. [raw](../../raw/links/llama-cpp-server-official-docs-20260707.md)

# ONNX Runtime GenAI

ONNX Runtime GenAI provides a configuration-driven runtime surface. Its config reference uses `genai_config.json` to carry model, tokenizer, provider, search, and generation settings. It names decoder past/present KV inputs and outputs, context length, provider settings, and search parameters such as beam count, sampling flags, top-k, top-p, temperature, repetition penalty, and early stopping. [raw](../../raw/links/onnx-runtime-genai-config-official-docs-20260707.md)

The Python API adds generation lifecycle evidence through `Config`, `Model`, `GeneratorParams`, `Generator`, and `Tokenizer`. `GeneratorParams` can set inputs, search options, and graph-capture settings; `Generator` can generate the next token, expose logits and generated tokens, rewind, check completion, and apply adapters. This is useful for local or embedded runtime configuration coverage, not for claims about centralized cluster admission or fleet autoscaling. [raw](../../raw/links/onnx-runtime-genai-config-official-docs-20260707.md)

# Coverage Use

Use this page as source-backed coverage for:

- `inference-runtime`: multi-project serving runtime mechanics, batching, KV-cache lifecycle, model loading/configuration, provider/hardware selection, OpenAI-compatible serving surfaces, and distributed inference knobs.
- `training-distributed`: only where vLLM RL weight syncing touches trainer-to-inference weight transfer; this page does not replace distributed training framework evidence.
- `network-storage-cluster`: only where PegaFlow's RDMA/SSD cache hierarchy or TensorRT NCCL collectives touch serving data movement; this page does not replace cluster storage or fabric coverage.
- `eval-observability-reliability`: only where TensorRT-LLM/Triton metrics or health endpoints are serving surfaces; this page does not replace observability platform or incident evidence.

Remaining gaps include production router/admission-control sources, autoscaling and model-placement evidence, canary or rollout mechanics, live serving incident postmortems, benchmark harness configuration, and broader runtime observability/tracing sources.

# Citations

- [vLLM README source note](../../raw/links/vllm-readme-official-20260707.md)
- [vLLM native RL APIs local capture](../../raw/crawler/nccl-vllm-blog/20260626T015715356602Z-vllm-ai-blog-2026-05-28-native-rl-apis-87d0cc671e.md)
- [vLLM PegaFlow local capture](../../raw/crawler/nccl-vllm-blog/20260626T015715357250Z-vllm-ai-blog-2026-05-18-pegaflow-c7d76fc4e2.md)
- [TensorRT-LLM KV-cache and serve source note](../../raw/links/tensorrt-llm-kv-cache-official-docs-20260707.md)
- [TensorRT multi-device inference local capture](../../raw/crawler/nccl-technical-blog/20260626T015704292802Z-developer-nvidia-com-blog-scaling-ai-inference-across-multiple-gpus-using-nvidia-tensorrt-6fabda0844.md)
- [Triton model repository and batcher source note](../../raw/links/triton-inference-server-batcher-official-docs-20260707.md)
- [llama.cpp source note](../../raw/links/llama-cpp-server-official-docs-20260707.md)
- [ONNX Runtime GenAI config/API source note](../../raw/links/onnx-runtime-genai-config-official-docs-20260707.md)
