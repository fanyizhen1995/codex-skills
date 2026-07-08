---
type: Reference
title: Inference Runtime Infrastructure
description: Source-backed reference for inference serving runtime mechanics and deployment controls across vLLM, TensorRT-LLM, Triton Inference Server, llama.cpp, ONNX Runtime GenAI, Ray Serve, Knative, and local TensorRT/vLLM captures.
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
  - ../../raw/links/ray-serve-deployment-control-official-docs-20260707.md
  - ../../raw/links/knative-serving-autoscaling-traffic-official-docs-20260707.md
  - ../../raw/links/kserve-inference-deployment-slo-trace-official-sources-20260707.md
  - ../../raw/links/inference-serving-incident-postmortem-sources-20260707.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/manifest-20260701-20260704.json
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208949433Z-github-com-sgl-project-sglang-issues-24220-d10eb2dd3d.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260704T021349139142Z-github-com-sgl-project-sglang-pull-29915-e345899286.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260703T021321693976Z-github-com-sgl-project-sglang-pull-29017-e3dfacd27b.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208950785Z-github-com-sgl-project-sglang-issues-23272-cd18614391.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208948083Z-github-com-sgl-project-sglang-issues-23342-a8af43b120.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227249888Z-github-com-sgl-project-sglang-issues-29812-e36ce78cbc.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260703T021321689913Z-github-com-sgl-project-sglang-issues-29954-58751d3526.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260704T021349137340Z-github-com-sgl-project-sglang-pull-27704-01338a2479.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227256930Z-github-com-sgl-project-sglang-pull-29211-98750e7397.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227258637Z-github-com-sgl-project-sglang-pull-25377-0207a52512.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260705T021410227684Z-github-com-sgl-project-sglang-issues-24456-05c913cb7d.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260707T233530899576Z-github-com-sgl-project-sglang-issues-23499-22090e3cb2.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260706T021453060525Z-github-com-sgl-project-sglang-pull-30053-c86bbf35fb.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260706T021453058039Z-github-com-sgl-project-sglang-issues-23937-c70c6119e4.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260706T021453058336Z-github-com-sgl-project-sglang-issues-24482-c660652870.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260707T233530899934Z-github-com-sgl-project-sglang-issues-21210-698d8324f1.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260707T233530906544Z-github-com-sgl-project-sglang-pull-28975-550e700977.md
updated: 2026-07-08
related:
  - ai-infra-coverage-map.md
  - ../projects/sglang.md
  - ../concepts/nvidia-green-context.md
---
# Summary

This reference broadens the `inference-runtime` layer beyond the existing SGLang and CUDA Green Context pages. It uses concise official source notes for vLLM, TensorRT-LLM, Triton Inference Server, llama.cpp, ONNX Runtime GenAI, Ray Serve, and Knative, plus existing local vLLM and NVIDIA TensorRT captures that were already in raw evidence.

The common boundary is serving-time infrastructure: request scheduling and batching, KV-cache lifetime, model repository or config loading, hardware/provider selection, distributed execution knobs, API-server surfaces, autoscaling, placement, and rollout traffic control. Model quality, prompt design, and application UX stay outside this page unless they directly affect runtime behavior.

# Runtime Surfaces

The sources split inference runtime into several repeated control surfaces:

- `request admission and batching`: vLLM continuous batching and chunked prefill, Triton dynamic batching, and TensorRT-LLM in-flight batching metrics all treat the server as an active scheduler rather than a passive wrapper. [raw](../../raw/links/vllm-readme-official-20260707.md) [raw](../../raw/links/triton-inference-server-batcher-official-docs-20260707.md) [raw](../../raw/links/tensorrt-llm-kv-cache-official-docs-20260707.md)
- `KV-cache lifecycle`: vLLM PagedAttention and prefix caching, TensorRT-LLM block reuse and offload, vLLM PegaFlow's external cache process, and ONNX Runtime GenAI's past/present KV names show that generated-token state is a first-class runtime asset. [raw](../../raw/links/vllm-readme-official-20260707.md) [raw](../../raw/crawler/nccl-vllm-blog/20260626T015715357250Z-vllm-ai-blog-2026-05-18-pegaflow-c7d76fc4e2.md) [raw](../../raw/links/tensorrt-llm-kv-cache-official-docs-20260707.md) [raw](../../raw/links/onnx-runtime-genai-config-official-docs-20260707.md)
- `model loading and execution target`: Triton uses a model repository with versioned model directories; ONNX Runtime GenAI uses `genai_config.json`; llama.cpp uses local/GGUF-style model loading; TensorRT and TensorRT-LLM use optimized runtime engines and serve commands. [raw](../../raw/links/triton-inference-server-batcher-official-docs-20260707.md) [raw](../../raw/links/onnx-runtime-genai-config-official-docs-20260707.md) [raw](../../raw/links/llama-cpp-server-official-docs-20260707.md) [raw](../../raw/links/tensorrt-llm-kv-cache-official-docs-20260707.md)
- `parallel and hardware placement`: vLLM exposes tensor, pipeline, data, expert, and context parallelism; TensorRT-LLM exposes tensor, pipeline, and expert parallel knobs in serving; TensorRT 11.0 adds multi-device inference with NCCL collectives; ONNX Runtime GenAI selects execution providers; llama.cpp spans local CPU/GPU backends. [raw](../../raw/links/vllm-readme-official-20260707.md) [raw](../../raw/links/tensorrt-llm-kv-cache-official-docs-20260707.md) [raw](../../raw/crawler/nccl-technical-blog/20260626T015704292802Z-developer-nvidia-com-blog-scaling-ai-inference-across-multiple-gpus-using-nvidia-tensorrt-6fabda0844.md) [raw](../../raw/links/onnx-runtime-genai-config-official-docs-20260707.md) [raw](../../raw/links/llama-cpp-server-official-docs-20260707.md)
- `deployment control`: Ray Serve adds request-driven autoscaling, deployment resource requests, accelerator-type inputs, placement-group/gang scheduling for multi-actor replicas, and Serve-controlled updates; Knative adds request-load autoscaling, immutable revisions, traffic percentages, latest-revision rollout, blue/green staging, and rollback-by-traffic-shift mechanics. [raw](../../raw/links/ray-serve-deployment-control-official-docs-20260707.md) [raw](../../raw/links/knative-serving-autoscaling-traffic-official-docs-20260707.md)

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

# Deployment Control Evidence

Ray Serve supplies the model-serving-specific deployment-control evidence in this round. Its autoscaling guide treats replica count as a function of deployment autoscaling config, with minimum and maximum replicas, target ongoing requests, and up/down delays. Its resource allocation docs put CPU, GPU, custom resources, accelerator type, and memory choices into the deployment actor options, which makes placement an explicit scheduling request rather than an inferred property of the model. [raw](../../raw/links/ray-serve-deployment-control-official-docs-20260707.md)

Ray Serve gang scheduling adds a stricter placement boundary for large serving replicas. When one replica needs several colocated actors, the source uses Ray placement-group bundles and placement-group strategy so the actors that make up the replica are scheduled as a unit. That is stronger model-placement evidence than generic Kubernetes node scheduling, but it still does not prove a particular cluster topology or production failure mode. [raw](../../raw/links/ray-serve-deployment-control-official-docs-20260707.md)

Ray Serve in-place update guidance and Knative revision traffic management fill rollout mechanics without claiming a complete canary incident record. Ray Serve separates lightweight config updates from replica-replacing updates. Knative Serving creates immutable revisions, can split traffic by percentage across revisions, supports latest-revision and blue/green rollout patterns, and preserves rollback-by-shifting traffic back to an earlier revision. Use the Knative facts as serving-control mechanics only; KServe-specific autoscaling and canary docs were probed again in r9 but not promoted because the sandbox could not resolve `kserve.github.io` or `github.com`, and no reliable page content was captured. [raw](../../raw/links/ray-serve-deployment-control-official-docs-20260707.md) [raw](../../raw/links/knative-serving-autoscaling-traffic-official-docs-20260707.md) [raw](../../raw/links/kserve-inference-deployment-slo-trace-official-sources-20260707.md)

# KServe And Postmortem Boundary

The r9 source notes keep KServe and production postmortem coverage open rather than converting blocked probes into claims. Local evidence is strong for Ray Serve and Knative deployment-control mechanics, SGLang request-id and abort observability, PD/Mooncake failure handling, and benchmark/profiling leads. It is still not source-backed KServe `InferenceService` autoscaling, KServe canary rollout, KServe rollback, or a complete inference-serving postmortem with impact, timeline, remediation, and ownership. [raw](../../raw/links/kserve-inference-deployment-slo-trace-official-sources-20260707.md) [raw](../../raw/links/inference-serving-incident-postmortem-sources-20260707.md)

# Production Operations Evidence

The local vLLM and SGLang evidence adds operational coverage beyond runtime feature lists:

- `external KV-cache lifecycle`: PegaFlow treats the host KV pool, SSD spill tier, RDMA resources, indexing state, and background tasks as a separate daemon-owned service. The source ties that boundary to engine crashes, rolling upgrades, model switches, multi-engine sharing, cache-admission policy, HLL hit-rate ceilings, an internal RDMA production-cluster transfer measurement, and a public H800 benchmark. Keep the performance numbers scoped to those documented workloads and setups. [raw](../../raw/crawler/nccl-vllm-blog/20260626T015715357250Z-vllm-ai-blog-2026-05-18-pegaflow-c7d76fc4e2.md)
- `rollout and weight-sync control`: the vLLM native RL API capture standardizes trainer-to-inference weight transfer into initialization, start, update, and finish phases with NCCL or CUDA IPC backends. It also adds pause/resume keep mode and a DPEP two-phase pause protocol so asynchronous RL deployments can update weights without discarding in-flight requests or deadlocking data-parallel ranks. The validation source describes a P/D disaggregated 16 x 8-H200 node inference setup, vLLM router, CPU KV offload, and 100+ training steps, so it is useful as deployment-shaped evidence rather than a generic reliability guarantee. [raw](../../raw/crawler/nccl-vllm-blog/20260626T015715356602Z-vllm-ai-blog-2026-05-28-native-rl-apis-87d0cc671e.md)
- `router trace and abort observability`: SGLang issue #24220 records the operator need for a unified request id across router, prefill worker, and decode worker. PR #29915 turns router-to-engine `/abort_request` calls into WARN-level per-event logs plus a Prometheus counter labeled by abort reason, and explicitly cites a production incident where premature aborts were visible only as volume, not cause. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208949433Z-github-com-sgl-project-sglang-issues-24220-d10eb2dd3d.md) [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260704T021349139142Z-github-com-sgl-project-sglang-pull-29915-e345899286.md)
- `PD disaggregation failure handling`: issue #23272 records sustained-load KV transfer failures in SGLang Model Gateway with Mooncake on L40S, while issue #23342 records an MI300X Mooncake/TCP router hang with healthy workers and network checks. PR #29017 narrows one router recovery path by cancelling the paired decode request when prefill fails, reducing the documented stuck decode path from the 300 second default timeout to roughly 4-8 seconds in its live 1P1D Mooncake validation. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208950785Z-github-com-sgl-project-sglang-issues-23272-cd18614391.md) [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208948083Z-github-com-sgl-project-sglang-issues-23342-a8af43b120.md) [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260703T021321693976Z-github-com-sgl-project-sglang-pull-29017-e3dfacd27b.md)
- `NIXL UCX disaggregated KV transfer crash`: issue #23499 records a DeepSeek-R1 FP8 disaggregated prefill+decode benchmark with 2 prefill nodes, 2 decode nodes, EP=TP=DP=8, and `disaggregation-transfer-backend: nixl`. The scheduler hit a segfault in the NIXL UCX worker through UCX CUDA event handling while sending KV chunks; the page distinguishes later Gloo broadcast and bootstrap errors as consequences of the crashed scheduler process. Treat this as transport-path troubleshooting evidence, not as a complete root-cause or workaround record. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260707T233530899576Z-github-com-sgl-project-sglang-issues-23499-22090e3cb2.md)
- `HiCache bootstrap abort cleanup`: PR #30053 records a narrow merged fix for `disagg_prefill_bootstrap_queue` aborts. Before the fix, a request could run `_prefetch_kvcache()` before entering the bootstrap queue, then abort without `release_aborted_request()`, leaking `prefetch_tokens_occupied` and an `ongoing_prefetch` entry until storage prefetch was permanently rate-limited for the process. The snapshot proves the page-level fix boundary only; it does not prove every HiCache abort lifecycle. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260706T021453060525Z-github-com-sgl-project-sglang-pull-30053-c86bbf35fb.md)
- `KV-transfer metric semantics`: issue #23937 records that `SchedulerReqTimeStats.compute_and_observe_kv_transfer_metrics` used request completion time instead of `prefill_kv_transfer_finish_time` for transfer latency, so decode time could be included in the KV-transfer window and reported transfer speed could look much slower than actual transfer. This is useful observability semantics for disaggregated serving, but it is not a production SLO, alert threshold, or measured network benchmark. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260706T021453058039Z-github-com-sgl-project-sglang-issues-23937-c70c6119e4.md)
- `Mooncake Store on Ascend 910B3`: issue #24482 records scheduler initialization failure when Mooncake Store is used as HiCache storage on Ascend 910B3 with dummy-client communication. The failure occurs when NPU host memory allocated through pinned-memory mechanisms cannot be found in Mooncake's registered shared-memory pool, causing buffer registration to fail and the scheduler to crash. The proposed direction is an NPU allocation path through Mooncake's host allocator so zero-copy semantics are not broken by an extra pin-memory copy. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260706T021453058336Z-github-com-sgl-project-sglang-issues-24482-c660652870.md)
- `EAGLE DP-attention padded-state crash`: issue #21210 records that EAGLE speculative decoding can reuse a `forward_batch` across decode-mode forwards while DP attention and MLP sync introduce padding. If padded metadata is not restored after a speculative step, the next `prepare_mlp_sync_batch()` can fail with a negative-dimension tensor error, kill the worker, and then cause router retry failures, health check failures, or training hangs in the reported GLM-4.7-Flash H800 setup. This is a page-level failure report rather than a verified final lifecycle record. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260707T233530899934Z-github-com-sgl-project-sglang-issues-21210-698d8324f1.md)
- `routed-output hot-path stalls`: SGLang issue #24456 records a Kimi K2 FP8 setup with TP=DP=EP=32 where enabling `--enable-return-routed-experts` made DeepEP dispatch/combine rows appear to have long collectives. The issue diagnosis is that a finishing DP rank can block the scheduler main thread on routed-expert gather, tensor serialization, and IPC send; the other ranks then wait at the next collective, so the trace labels waiting time as a collective bubble. The source estimates each long finished request can cost about 300-600 ms on the scheduler thread, or several decode steps in that setup. Treat this as issue-level hot-path attribution, not as proof of a merged fix or a general throughput benchmark. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260705T021410227684Z-github-com-sgl-project-sglang-issues-24456-05c913cb7d.md)
- `startup, cache, benchmark, and tracing leads`: issue #29812 shows decode warmup readiness blocked by UnifiedRadixCache plus HiCache restore state; issue #29954 shows a Blackwell/GLM-5.2 FP8 startup crash after a DeepGEMM dependency bump; PR #29211 fixes KV-event publisher port collisions under pure data parallelism; PR #25377 adds a HiCache DRAM/SSD L3 backend with cache-hit, TTFT, correctness, and reproduction details; PR #27704 adds profiling support plus benchmark argument fixes for diffusion offline throughput; and PR #28975 adds an opt-in Triton FP8 sparse-MLA prefill path for GLM-5.1-MXFP4 on MI350X/gfx950 with profiler rationale plus TTFT and ITL benchmark tables. These are issue-level and PR-level operational leads, not replacements for full incident postmortems or general benchmark baselines. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227249888Z-github-com-sgl-project-sglang-issues-29812-e36ce78cbc.md) [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260703T021321689913Z-github-com-sgl-project-sglang-issues-29954-58751d3526.md) [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227256930Z-github-com-sgl-project-sglang-pull-29211-98750e7397.md) [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227258637Z-github-com-sgl-project-sglang-pull-25377-0207a52512.md) [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260704T021349137340Z-github-com-sgl-project-sglang-pull-27704-01338a2479.md) [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260707T233530906544Z-github-com-sgl-project-sglang-pull-28975-550e700977.md)

# Coverage Use

Use this page as source-backed coverage for:

- `inference-runtime`: multi-project serving runtime mechanics, batching, KV-cache lifecycle, model loading/configuration, provider/hardware selection, OpenAI-compatible serving surfaces, distributed inference knobs, Ray Serve autoscaling/resource/placement-group deployment controls, Knative revision traffic-split rollout mechanics, external KV-cache operations, rollout weight-sync control, router abort observability, PD disaggregation failure handling, NIXL/UCX KV-transfer crash evidence, HiCache bootstrap-abort cleanup, Mooncake Store Ascend NPU registration failure, EAGLE DP-attention crash evidence, routed-experts return hot-path stall diagnosis, benchmark/profiling harness leads, warmup/startup regression leads, and r9 blocked evidence for KServe/postmortem source probes.
- `training-distributed`: only where vLLM RL weight syncing touches trainer-to-inference weight transfer; this page does not replace distributed training framework evidence.
- `network-storage-cluster`: only where PegaFlow's RDMA/SSD cache hierarchy or TensorRT NCCL collectives touch serving data movement; this page does not replace cluster storage or fabric coverage.
- `eval-observability-reliability`: only where TensorRT-LLM/Triton metrics or health endpoints are serving surfaces; this page does not replace observability platform or incident evidence.

Remaining gaps include KServe-specific autoscaling and canary rollout documentation, production failure/rollback evidence around autoscaling or rollout controls, full production postmortems with service impact and remediation, live trace/profiling artifacts tied to SLOs, and a decision on whether SGLang scheduled crawler supplement leads need a full API refresh with comments and review comments. The r9 KServe and incident/postmortem notes are blocked-source evidence, not closure evidence.

# Citations

- [vLLM README source note](../../raw/links/vllm-readme-official-20260707.md)
- [vLLM native RL APIs local capture](../../raw/crawler/nccl-vllm-blog/20260626T015715356602Z-vllm-ai-blog-2026-05-28-native-rl-apis-87d0cc671e.md)
- [vLLM PegaFlow local capture](../../raw/crawler/nccl-vllm-blog/20260626T015715357250Z-vllm-ai-blog-2026-05-18-pegaflow-c7d76fc4e2.md)
- [TensorRT-LLM KV-cache and serve source note](../../raw/links/tensorrt-llm-kv-cache-official-docs-20260707.md)
- [TensorRT multi-device inference local capture](../../raw/crawler/nccl-technical-blog/20260626T015704292802Z-developer-nvidia-com-blog-scaling-ai-inference-across-multiple-gpus-using-nvidia-tensorrt-6fabda0844.md)
- [Triton model repository and batcher source note](../../raw/links/triton-inference-server-batcher-official-docs-20260707.md)
- [llama.cpp source note](../../raw/links/llama-cpp-server-official-docs-20260707.md)
- [ONNX Runtime GenAI config/API source note](../../raw/links/onnx-runtime-genai-config-official-docs-20260707.md)
- [Ray Serve deployment control source note](../../raw/links/ray-serve-deployment-control-official-docs-20260707.md)
- [Knative Serving autoscaling and traffic source note](../../raw/links/knative-serving-autoscaling-traffic-official-docs-20260707.md)
- [KServe inference deployment SLO trace source probe](../../raw/links/kserve-inference-deployment-slo-trace-official-sources-20260707.md)
- [Inference serving incident and postmortem source probe](../../raw/links/inference-serving-incident-postmortem-sources-20260707.md)
- [SGLang scheduled crawler supplement manifest, 2026-07-01 to 2026-07-04](../../raw/crawler/sglang-github-closed-issues-prs/manifest-20260701-20260704.json)
- [SGLang issue #24220 request-id tracing](../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208949433Z-github-com-sgl-project-sglang-issues-24220-d10eb2dd3d.md)
- [SGLang PR #29915 router abort observability](../../raw/crawler/sglang-github-closed-issues-prs/20260704T021349139142Z-github-com-sgl-project-sglang-pull-29915-e345899286.md)
- [SGLang PR #29017 PD router paired-decode cancellation](../../raw/crawler/sglang-github-closed-issues-prs/20260703T021321693976Z-github-com-sgl-project-sglang-pull-29017-e3dfacd27b.md)
- [SGLang issue #23272 Mooncake KV transfer failure](../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208950785Z-github-com-sgl-project-sglang-issues-23272-cd18614391.md)
- [SGLang issue #23342 Mooncake TCP router hang](../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208948083Z-github-com-sgl-project-sglang-issues-23342-a8af43b120.md)
- [SGLang issue #29812 decode warmup hang](../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227249888Z-github-com-sgl-project-sglang-issues-29812-e36ce78cbc.md)
- [SGLang issue #29954 DeepGEMM startup regression](../../raw/crawler/sglang-github-closed-issues-prs/20260703T021321689913Z-github-com-sgl-project-sglang-issues-29954-58751d3526.md)
- [SGLang PR #27704 benchmark profiling support](../../raw/crawler/sglang-github-closed-issues-prs/20260704T021349137340Z-github-com-sgl-project-sglang-pull-27704-01338a2479.md)
- [SGLang PR #29211 KV-event publisher port collision fix](../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227256930Z-github-com-sgl-project-sglang-pull-29211-98750e7397.md)
- [SGLang PR #25377 HiCache UMBP storage backend](../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227258637Z-github-com-sgl-project-sglang-pull-25377-0207a52512.md)
- [SGLang issue #24456 routed-experts return hot-path stall](../../raw/crawler/sglang-github-closed-issues-prs/20260705T021410227684Z-github-com-sgl-project-sglang-issues-24456-05c913cb7d.md)
- [SGLang issue #23499 NIXL UCX worker segfault](../../raw/crawler/sglang-github-closed-issues-prs/20260707T233530899576Z-github-com-sgl-project-sglang-issues-23499-22090e3cb2.md)
- [SGLang PR #30053 HiCache prefetch cleanup](../../raw/crawler/sglang-github-closed-issues-prs/20260706T021453060525Z-github-com-sgl-project-sglang-pull-30053-c86bbf35fb.md)
- [SGLang issue #23937 KV transfer metric window](../../raw/crawler/sglang-github-closed-issues-prs/20260706T021453058039Z-github-com-sgl-project-sglang-issues-23937-c70c6119e4.md)
- [SGLang issue #24482 Ascend 910B3 Mooncake Store buffer registration](../../raw/crawler/sglang-github-closed-issues-prs/20260706T021453058336Z-github-com-sgl-project-sglang-issues-24482-c660652870.md)
- [SGLang issue #21210 EAGLE DP attention padded-state crash](../../raw/crawler/sglang-github-closed-issues-prs/20260707T233530899934Z-github-com-sgl-project-sglang-issues-21210-698d8324f1.md)
- [SGLang PR #28975 AMD MI350X sparse-MLA prefill profiling](../../raw/crawler/sglang-github-closed-issues-prs/20260707T233530906544Z-github-com-sgl-project-sglang-pull-28975-550e700977.md)
