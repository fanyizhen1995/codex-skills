---
type: RawSource
title: llama.cpp README And Server Runtime
source_kind: web
url: https://github.com/ggml-org/llama.cpp
captured: 2026-07-07
status: ingested
---
# Source

Official llama.cpp GitHub repository README: https://github.com/ggml-org/llama.cpp

Captured as a concise source note for `ai_infra` inference-runtime coverage. The full external page was not mirrored; the durable facts below are paraphrased from the official source.

# Captured Facts

- llama.cpp positions itself as LLM inference in C/C++ with minimal setup, local and cloud execution options, and broad hardware support.
- The README documents `llama-cli` for local generation and `llama-server` for server mode.
- `llama-server` provides an OpenAI-compatible web server surface for local models.
- The repository documents GGUF model use, local file loading, and model download from Hugging Face style model identifiers.
- llama.cpp documents integer quantization support across multiple bit widths, including small quantized formats used for local deployment.
- Hardware backend coverage in the README includes CPU execution, Apple silicon acceleration, CUDA, HIP, Vulkan, SYCL, MUSA, CANN, OpenCL, and hybrid CPU/GPU execution.
- The README describes llama.cpp as dependency-light and suitable for running many model families locally, which makes it an inference runtime and deployment artifact rather than a distributed serving control plane.

# Use In Wiki

Use this source note for llama.cpp claims about local/server runtime mode, OpenAI-compatible serving, GGUF model loading, quantization, hardware backend range, and the boundary between local inference runtime and fleet-scale serving.
