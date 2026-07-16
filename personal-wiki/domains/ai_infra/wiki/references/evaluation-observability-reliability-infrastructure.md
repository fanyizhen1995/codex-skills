---
type: Reference
title: Evaluation Observability Reliability Infrastructure
description: Source-backed reference for LLM evaluation harnesses, GenAI tracing, alerting mechanics, observability platforms, and platform profiling signals.
domain: ai_infra
status: reviewed
aliases:
  - LLM evaluation observability infrastructure
  - GenAI tracing infrastructure
  - evaluation reliability infrastructure
tags:
  - eval-observability-reliability
  - evaluation
  - observability
  - tracing
  - profiling
source_refs:
  - ../../raw/links/opentelemetry-genai-semconv-official-20260707.md
  - ../../raw/links/langsmith-observability-evaluation-official-20260707.md
  - ../../raw/links/phoenix-evaluation-tracing-official-20260707.md
  - ../../raw/links/ragas-evaluation-metrics-official-20260707.md
  - ../../raw/links/lm-evaluation-harness-official-20260707.md
  - ../../raw/links/nvidia-dcgm-gpu-telemetry-official-20260707.md
  - ../../raw/links/nvidia-nsight-systems-profiling-official-20260707.md
  - ../../raw/links/evaluation-slo-alerting-official-sources-20260707.md
  - ../../raw/links/non-nvidia-platform-observability-official-sources-20260707.md
  - ../../raw/links/kserve-inference-deployment-slo-trace-official-sources-20260707.md
  - ../../raw/links/inference-serving-incident-postmortem-sources-20260707.md
  - ../../raw/links/rag-propagation-drift-alert-cost-evidence-20260707.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260706T021453058039Z-github-com-sgl-project-sglang-issues-23937-c70c6119e4.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260707T233530906544Z-github-com-sgl-project-sglang-pull-28975-550e700977.md
  - ../../raw/crawler/nccl-aws-hpc-blog/20260705T041042318130Z-aws-amazon-com-blogs-hpc-the-complete-picture-unified-monitoring-for-aws-parallel-computin-ba8cb4538e.md
  - ../../raw/crawler/nccl-nvidia-blog-wide/20260705T041056436811Z-developer-nvidia-com-blog-hardware-rooted-ai-security-that-wont-slow-you-down-87ae507096.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260708T233633803455Z-github-com-sgl-project-sglang-pull-29716-b6242f612e.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260708T233633800329Z-github-com-sgl-project-sglang-pull-30255-d5016bf405.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260714T234021668233Z-github-com-sgl-project-sglang-pull-30351-df076892cc.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260714T234021666327Z-github-com-sgl-project-sglang-pull-30457-59df9d512c.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260713T234005167501Z-github-com-sgl-project-sglang-pull-31001-8e73a7e57f.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260715T234028353201Z-github-com-sgl-project-sglang-pull-30355-31931c5d7d.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260715T234028355612Z-github-com-sgl-project-sglang-pull-30997-8fda1aa71b.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260715T234028357774Z-github-com-sgl-project-sglang-pull-31333-b47d00a41d.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260715T234028379398Z-github-com-sgl-project-sglang-pull-31272-4ddb017271.md
updated: 2026-07-16
related:
  - ai-infra-coverage-map.md
  - data-rag-pipeline-infrastructure.md
  - inference-runtime-infrastructure.md
  - nccl-technical-blog-network-observability.md
  - ../references/sglang-github-closed-issues-prs.md
---
# Summary

This reference broadens the `eval-observability-reliability` layer beyond NCCL Inspector, SGLang operational evidence, and RAG-specific Langfuse coverage. It groups primary-source notes around six infrastructure surfaces: portable GenAI telemetry schemas, application trace stores, evaluation harnesses, SLO/alert-routing mechanics, platform profiling, and non-NVIDIA accelerator observability. It also records bounded benchmark-context evidence when a source exposes setup, metrics, and caveats without treating the source result as a local baseline.

The boundary is operational infrastructure. Prompt-writing advice, model architecture details, and benchmark leaderboard claims are outside this page unless the source records run configuration, datasets, metrics, traces, or platform telemetry.

# Telemetry Schema

OpenTelemetry GenAI semantic conventions provide the portable telemetry envelope. They define conventions for GenAI traces, metrics, and events across client calls, server spans, agents, tools, embeddings, and retrieval operations. That makes OpenTelemetry the shared schema layer for recording model-provider metadata and orchestration boundaries across LLM applications. [raw](../../raw/links/opentelemetry-genai-semconv-official-20260707.md)

This is different from NCCL or Spectrum-X observability. NCCL technical-blog evidence records communication-library and fabric-level telemetry such as NCCL Inspector metrics, Prometheus/Grafana dashboards, RAS state, and switch/NIC signals. OpenTelemetry GenAI records application and model-call semantics above that layer. [wiki](nccl-technical-blog-network-observability.md) [raw](../../raw/links/opentelemetry-genai-semconv-official-20260707.md)

# SLO And Alert Routing Mechanics

Prometheus alerting rules, Alertmanager routing, Grafana notification policies, and Grafana SLO documentation add generic but reusable alerting mechanics. Prometheus rules turn PromQL expressions into alert states, attach labels and annotations, and use pending and keep-firing windows to stabilize alerts. Alertmanager and Grafana then route, group, mute, repeat, and deliver notifications through receiver or contact-point policies. [raw](../../raw/links/evaluation-slo-alerting-official-sources-20260707.md)

Grafana SLO documentation frames reliability around SLIs, SLO targets, time windows, burn-rate views, error-budget views, and alert rules. Grafana AI Observability adds LLM-specific metrics and dashboard surfaces such as request activity, latency, time to first token, error rate, token use, cost, cache behavior, quality scores, and example alerts for error rate, p95 latency, spend, and evaluation-score changes. [raw](../../raw/links/evaluation-slo-alerting-official-sources-20260707.md)

This closes only the alerting-mechanics gap. These sources do not prove a local production LLM service objective, a validated alert threshold, a real escalation tree, or an incident response process. Promote a production SLO only when the evidence includes the service, SLI definition, target, time window, alert threshold, route/escalation owner, and observed run or incident context. [raw](../../raw/links/evaluation-slo-alerting-official-sources-20260707.md)

The r10 RAG operations probe applied the same rule to retrieval-quality alerting. Local evidence covers Ragas metrics, LangSmith and Phoenix traces, Langfuse RAG evaluation, OpenTelemetry GenAI retrieval spans, and Grafana AI Observability quality-score and cost alert examples, but the probe did not capture a primary artifact with retrieval metric thresholds, notification route, owner, and observed RAG run. [raw](../../raw/links/rag-propagation-drift-alert-cost-evidence-20260707.md)

The r9 KServe and incident/postmortem source probes did not add service-specific production SLO evidence. They record that local sources already cover generic SLO and trace mechanics, but the selected KServe URLs and external incident source path were blocked by DNS or lacked captured content in this generator attempt. Treat those notes as gap evidence until a later capture includes the service, trace or metric artifact, chosen SLO/threshold, escalation owner, and observed run or incident context. [raw](../../raw/links/kserve-inference-deployment-slo-trace-official-sources-20260707.md) [raw](../../raw/links/inference-serving-incident-postmortem-sources-20260707.md)

The July 6-7 SGLang page supplement adds two useful but bounded observability leads. Issue #23937 is metric-semantics evidence: a KV-cache transfer speed metric can be biased if its latency window ends at request completion instead of `prefill_kv_transfer_finish_time`, because decode time is then included in the transfer window. PR #28975 is benchmark/profiling evidence for an opt-in GLM-5.1-MXFP4 MI350X/gfx950 sparse-MLA prefill kernel: it includes profiler rationale plus accuracy, TTFT, ITL, and E2EL tables for the stated setup. Neither source closes the production SLO gap, because neither records a service objective, validated alert threshold, escalation route, or incident lifecycle. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260706T021453058039Z-github-com-sgl-project-sglang-issues-23937-c70c6119e4.md) [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260707T233530906544Z-github-com-sgl-project-sglang-pull-28975-550e700977.md)

The July 10-14 SGLang page supplement adds metric-semantics evidence for MLA KV-transfer fan-out. PR #30351 records that `sglang:kv_transfer_total_mb` and `sglang:kv_transfer_speed_gb_s` were computed from a single KV cache transfer even when one prefill sender replicated the same full KV cache to multiple decode ranks, so the reported transfer speed could appear too low by the decode fan-out factor. The fix derives a replication factor at the connector registration barrier for Mooncake, NIXL, and Mori and applies it to transferred bytes. This improves diagnostic semantics for the metric, but it is not a production SLO, alert threshold, or network benchmark. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260714T234021668233Z-github-com-sgl-project-sglang-pull-30351-df076892cc.md)

# Trace And Experiment Stores

LangSmith and Phoenix provide trace-store and experiment workflows for LLM applications. LangSmith records nested runs for model calls, tools, retrievers, chains, inputs, outputs, latency, errors, metadata, feedback, datasets, evaluators, and experiment results. Phoenix similarly documents LLM traces across model, tool, retriever, and application spans, plus dataset-backed experiments and evaluator scores. [raw](../../raw/links/langsmith-observability-evaluation-official-20260707.md) [raw](../../raw/links/phoenix-evaluation-tracing-official-20260707.md)

These sources support a reusable operator pattern: preserve request traces and offline experiment outputs in one place so an application, retrieval, prompt, model, or serving change can be compared against earlier runs. That sentence is synthesis across LangSmith, Phoenix, Ragas, and lm-evaluation-harness sources; no single source proves every part of the pattern. [raw](../../raw/links/langsmith-observability-evaluation-official-20260707.md) [raw](../../raw/links/phoenix-evaluation-tracing-official-20260707.md) [raw](../../raw/links/ragas-evaluation-metrics-official-20260707.md) [raw](../../raw/links/lm-evaluation-harness-official-20260707.md)

# Evaluation Harnesses

Ragas and lm-evaluation-harness supply the evaluation-harness side of the layer. Ragas documents RAG and LLM evaluation around datasets, metrics, and scored outputs for retrieval and generation quality. lm-evaluation-harness documents benchmark tasks, model backend adapters, CLI run parameters, device placement, output paths, and task metrics. [raw](../../raw/links/ragas-evaluation-metrics-official-20260707.md) [raw](../../raw/links/lm-evaluation-harness-official-20260707.md)

For infrastructure use, the important boundary is run metadata. A benchmark result is not durable evidence unless the harness records the task set, model backend, runtime arguments, device or served-model path, output artifact, and enough environment context to compare later runs. The local source notes support that requirement at the harness-mechanics level; they do not supply a local benchmark corpus or accepted performance baseline. [raw](../../raw/links/lm-evaluation-harness-official-20260707.md) [raw](../../raw/links/nvidia-nsight-systems-profiling-official-20260707.md)

# Benchmark Context Boundary

The NVIDIA confidential-computing capture contributes benchmark context, not an accepted local benchmark baseline. It records a CC Off versus CC On comparison for HGX B300 with Blackwell Ultra, Qwen 3.5 397B-A17B at FP8 precision, VM GPU passthrough, Intel TDX, SGLang server, CUDA 13.2, SGLang `docker.io/lmsysorg/sglang:v0.5.12-cu130`, NCCL v2.28.9-1, Docker plus NVIDIA Container Toolkit, input/output lengths of 1024/1024 and 8192/1024, and 4 through 256 concurrent requests. The metrics listed are output throughput per GPU, median TTFT, and median TPOT, while the table reports throughput and TPOT deltas versus CC Off. Use this as source-visible benchmark context for confidential inference only; do not convert it into a local result, a general SLO, a validated alert threshold, a production incident/postmortem, an MLCommons submission, or a product ranking. [raw](../../raw/crawler/nccl-nvidia-blog-wide/20260705T041056436811Z-developer-nvidia-com-blog-hardware-rooted-ai-security-that-wont-slow-you-down-87ae507096.md)

The July 8 SGLang page supplement adds two more source-owned benchmark contexts. PR #29716 evaluates optional HiCacheFile metadata caching on a shared Lustre filesystem with 157,195 cache files and reports TTFT tail-latency changes while documenting startup scanning, cache-hit path, and eviction invalidation tests. PR #30255 evaluates a DSV4 sparse prefill Triton recompilation mitigation with AgentX, direct kernel, alternating metadata sweep, and GSM8K accuracy context after moving C128 metadata capacity and sparse combiner `top_k` from compile-time constants to runtime scalars. These sources are useful for benchmark-environment and profiling-context patterns, but they are still page-level PR evidence, not local benchmark results, MLCommons submissions, service SLOs, alert thresholds, product rankings, or production guarantees. [HiCacheFile raw](../../raw/crawler/sglang-github-closed-issues-prs/20260708T233633803455Z-github-com-sgl-project-sglang-pull-29716-b6242f612e.md) [DSV4 raw](../../raw/crawler/sglang-github-closed-issues-prs/20260708T233633800329Z-github-com-sgl-project-sglang-pull-30255-d5016bf405.md)

The July 10-14 SGLang pages add two more source-scoped validation contexts. PR #30457 includes GSM8K and throughput tables for `scheduler_recv_interval` under DP attention on a DeepSeek-R1-MXFP4 MI355X setup, while PR #31001 includes before/after reproduction output for a GLM-5.2-NVFP4 FlashInfer `routing_bias` dtype fix on 4 x B300. Use these as examples of page-visible run metadata and validation context only; they are not local benchmarks, MLCommons results, service SLOs, alert thresholds, product rankings, or general performance guarantees. [#30457](../../raw/crawler/sglang-github-closed-issues-prs/20260714T234021666327Z-github-com-sgl-project-sglang-pull-30457-59df9d512c.md) [#31001](../../raw/crawler/sglang-github-closed-issues-prs/20260713T234005167501Z-github-com-sgl-project-sglang-pull-31001-8e73a7e57f.md)

The July 15 SGLang pages add source-scoped validation and diagnostic contexts. PR #30355 records MI355X/gfx950 DeepSeek-R1-MXFP4 validation for the triton DeepSeek MLA backend after selected-backend gating, while explicitly leaving triton plus EAGLE speculative decode out of scope. PR #30997 records Qwen3.5-397B-A17B-FP8 heterogeneous attention-TP accuracy context for GDN conv-state and GQA replicated-KV head-map transfer fixes. PR #31333 documents CUDA device coredump output and request pickle behavior behind `--crash-dump-folder`; PR #31272 adds `Server-Timing: engine.worker` attribution for selected downstream workers on dispatch-stage router errors. These are page-level validation and diagnostic surfaces, not local benchmark baselines, production SLOs, alert thresholds, product rankings, or incident postmortems. [#30355](../../raw/crawler/sglang-github-closed-issues-prs/20260715T234028353201Z-github-com-sgl-project-sglang-pull-30355-31931c5d7d.md) [#30997](../../raw/crawler/sglang-github-closed-issues-prs/20260715T234028355612Z-github-com-sgl-project-sglang-pull-30997-8fda1aa71b.md) [#31333](../../raw/crawler/sglang-github-closed-issues-prs/20260715T234028357774Z-github-com-sgl-project-sglang-pull-31333-b47d00a41d.md) [#31272](../../raw/crawler/sglang-github-closed-issues-prs/20260715T234028379398Z-github-com-sgl-project-sglang-pull-31272-4ddb017271.md)

# Platform Profiling And Health

DCGM and Nsight Systems cover the platform side that LLM trace stores cannot see by themselves. DCGM provides GPU health, telemetry, diagnostics, field values, and profiling signals for data-center GPU systems. Nsight Systems provides timeline-oriented CPU/GPU profiling for CUDA workloads, host execution, synchronization, memory operations, kernels, and process/thread behavior. [raw](../../raw/links/nvidia-dcgm-gpu-telemetry-official-20260707.md) [raw](../../raw/links/nvidia-nsight-systems-profiling-official-20260707.md)

Use these sources to connect evaluation or trace anomalies with platform signals, not to assert model quality. For example, a regression triage workflow can pair evaluator scores and request traces with DCGM health fields or an Nsight Systems profile when latency, synchronization, or GPU activity changes. That is a synthesis pattern across the cited observability and profiling sources, not a vendor-specific product claim. [raw](../../raw/links/langsmith-observability-evaluation-official-20260707.md) [raw](../../raw/links/nvidia-dcgm-gpu-telemetry-official-20260707.md) [raw](../../raw/links/nvidia-nsight-systems-profiling-official-20260707.md)

# Cluster Observability Dashboards

The AWS Parallel Computing Service monitoring capture adds dashboard-level observability evidence for HPC and AI clusters. Its architecture sends Slurm, EFA, Node, and DCGM exporter metrics to Amazon Managed Service for Prometheus, displays them in Amazon Managed Grafana, and pulls instance details from Amazon CloudWatch Logs. The dashboard set is useful coverage for Jobs, Nodes, GPUs, Slurm, Amazon FSx for Lustre, Logs, Partitions, and EFA views, including GPU load/consumed memory, searchable logs, partition state, EFA nodes, RDMA reads/writes, processed traffic, and dropped-packet visibility. [raw](../../raw/crawler/nccl-aws-hpc-blog/20260705T041042318130Z-aws-amazon-com-blogs-hpc-the-complete-picture-unified-monitoring-for-aws-parallel-computin-ba8cb4538e.md)

Keep this as observability-solution evidence. It does not define service-specific LLM SLOs, validated alert thresholds, routing or escalation ownership, production incident timelines, or benchmark acceptance criteria. Pair it with application traces, evaluation artifacts, or incident records before using dashboard views as reliability claims. [raw](../../raw/crawler/nccl-aws-hpc-blog/20260705T041042318130Z-aws-amazon-com-blogs-hpc-the-complete-picture-unified-monitoring-for-aws-parallel-computin-ba8cb4538e.md)

# Non-NVIDIA Platform Observability

AMD Device Metrics Exporter and ROCm/AMD SMI add AMD-side observability surfaces. The AMD exporter documents Prometheus-format GPU and NIC metrics, Kubernetes and Slurm deployment paths, and telemetry for utilization, memory, clocks, power, energy, VRAM, PCIe bandwidth, PCIe errors, RDMA, congestion, CNP, ECN, and NIC queue signals. ROCm SMI and AMD SMI provide system-management interfaces for querying driver/GPU information and controlling GPU applications. [raw](../../raw/links/non-nvidia-platform-observability-official-sources-20260707.md)

Intel Gaudi Prometheus Metric Exporter adds a second non-NVIDIA accelerator telemetry path. It documents Docker and Kubernetes deployment, kube-prometheus ServiceMonitor integration, and metrics for device identity, clocks, ECC, energy, memory, NIC ports, PCIe throughput/replay counters, power, temperatures, thermal thresholds, and utilization. [raw](../../raw/links/non-nvidia-platform-observability-official-sources-20260707.md)

Use this as non-NVIDIA observability mechanics only. It does not prove production AMD, TPU, XPU, or Gaudi reliability, local benchmark performance, alert thresholds, or postmortem remediation. The Google Cloud TPU monitoring source was considered but not promoted because the web probe did not return reliable content in this run. [raw](../../raw/links/non-nvidia-platform-observability-official-sources-20260707.md)

# Adjacent Coverage

[Data RAG Pipeline Infrastructure](data-rag-pipeline-infrastructure.md) already covers Langfuse for RAG-specific traces, retrieval steps, datasets, feedback, and evaluation. This page uses LangSmith, Phoenix, Ragas, and lm-evaluation-harness to broaden beyond RAG-only observability and to make evaluation harness mechanics explicit. [wiki](data-rag-pipeline-infrastructure.md)

[Inference Runtime Infrastructure](inference-runtime-infrastructure.md) records runtime health or metrics surfaces for vLLM, TensorRT-LLM, Triton, llama.cpp, and ONNX Runtime GenAI. This page does not repeat those serving mechanics; it covers the evaluation and trace systems that inspect application behavior around those runtimes. [wiki](inference-runtime-infrastructure.md)

[NCCL Technical Blog Network Observability](nccl-technical-blog-network-observability.md) remains the stronger source for communication and NVIDIA fabric observability. This page adds non-NCCL sources for LLM traces, evaluation datasets, benchmark harnesses, SLO/alert routing mechanics, DCGM/Nsight telemetry, and AMD/Gaudi platform metrics. [wiki](nccl-technical-blog-network-observability.md)

# Coverage Use

Use this page as source-backed coverage for:

- `eval-observability-reliability`: GenAI telemetry schemas, LLM application trace stores, datasets, evaluator outputs, benchmark task/run metadata, SLO/alerting mechanics, GPU health telemetry, CPU/GPU profiling, and non-NVIDIA accelerator metrics.
- `eval-observability-reliability`: AWS PCS dashboard evidence for Managed Grafana, Managed Prometheus, CloudWatch Logs, Slurm/EFA/Node/DCGM exporters, and Jobs/Nodes/GPUs/Slurm/FSx/EFA/Logs views.
- `eval-observability-reliability`: bounded NVIDIA confidential-inference benchmark context where the source records environment, software stack, workload parameters, and throughput/TPOT deltas, without treating those numbers as local benchmark acceptance criteria.
- `eval-observability-reliability`: bounded SGLang HiCacheFile and DSV4 sparse prefill benchmark/profiling contexts where the sources record workload, filesystem or runtime setup, tests, and caveats, without treating those numbers as local benchmark acceptance criteria.
- `eval-observability-reliability`: SGLang KV-transfer metric fan-out semantics from PR #30351; page-scoped validation contexts from #30457, #31001, #30355, and #30997; CUDA crash-dump documentation from #31333; and Server-Timing worker attribution from #31272, without treating them as alert thresholds, production SLOs, local benchmark acceptance criteria, or postmortems.
- `data-rag-vector`: only where Ragas, Phoenix, or LangSmith traces explain RAG evaluation and retrieval-quality signals; keep data ingestion and embedding refresh in [Data RAG Pipeline Infrastructure](data-rag-pipeline-infrastructure.md).
- `inference-runtime`: only where evaluation traces or platform profiles inspect runtime behavior; keep runtime scheduler, batching, KV-cache, and model-loading mechanics in [Inference Runtime Infrastructure](inference-runtime-infrastructure.md).
- `hardware-accelerator`: only for DCGM and Nsight platform telemetry/profiling signals; accelerator SKU and parameter evidence stays in the compute accelerator pages.

Remaining gaps include production SLO definitions, validated alert thresholds and routing ownership, incident/postmortem sources, benchmark environment manifests with captured local results, TPU/XPU production observability, and evaluation dataset retention/access audit run evidence. The r9 KServe and inference incident/postmortem notes preserve blocked-source evidence for the serving trace/SLO gap, while the SGLang metric-window, KV-transfer fan-out, MI350X/MI355 profiling, heterogeneous attention-TP, CUDA crash-dump, Server-Timing, HiCacheFile metadata-cache, DSV4 sparse-prefill, DP-attention scheduler, GLM/DeepSeek FlashInfer, and NVIDIA confidential-inference pages add useful page-level semantics or benchmark context but do not close the production SLO or local benchmark-baseline gaps.

# Citations

- [OpenTelemetry GenAI semantic conventions source note](../../raw/links/opentelemetry-genai-semconv-official-20260707.md)
- [LangSmith observability and evaluation source note](../../raw/links/langsmith-observability-evaluation-official-20260707.md)
- [Phoenix tracing and evaluation source note](../../raw/links/phoenix-evaluation-tracing-official-20260707.md)
- [Ragas evaluation metrics source note](../../raw/links/ragas-evaluation-metrics-official-20260707.md)
- [lm-evaluation-harness source note](../../raw/links/lm-evaluation-harness-official-20260707.md)
- [NVIDIA DCGM source note](../../raw/links/nvidia-dcgm-gpu-telemetry-official-20260707.md)
- [NVIDIA Nsight Systems source note](../../raw/links/nvidia-nsight-systems-profiling-official-20260707.md)
- [Evaluation SLO and alerting source note](../../raw/links/evaluation-slo-alerting-official-sources-20260707.md)
- [Non-NVIDIA platform observability source note](../../raw/links/non-nvidia-platform-observability-official-sources-20260707.md)
- [KServe inference deployment SLO trace source probe](../../raw/links/kserve-inference-deployment-slo-trace-official-sources-20260707.md)
- [Inference serving incident and postmortem source probe](../../raw/links/inference-serving-incident-postmortem-sources-20260707.md)
- [RAG propagation, drift, alerting, and cost evidence probe](../../raw/links/rag-propagation-drift-alert-cost-evidence-20260707.md)
- [SGLang issue #23937 KV transfer metric window](../../raw/crawler/sglang-github-closed-issues-prs/20260706T021453058039Z-github-com-sgl-project-sglang-issues-23937-c70c6119e4.md)
- [SGLang PR #28975 AMD MI350X sparse-MLA prefill profiling](../../raw/crawler/sglang-github-closed-issues-prs/20260707T233530906544Z-github-com-sgl-project-sglang-pull-28975-550e700977.md)
- [AWS Parallel Computing Service monitoring capture](../../raw/crawler/nccl-aws-hpc-blog/20260705T041042318130Z-aws-amazon-com-blogs-hpc-the-complete-picture-unified-monitoring-for-aws-parallel-computin-ba8cb4538e.md)
- [NVIDIA Blackwell confidential-inference raw capture](../../raw/crawler/nccl-nvidia-blog-wide/20260705T041056436811Z-developer-nvidia-com-blog-hardware-rooted-ai-security-that-wont-slow-you-down-87ae507096.md)
- [SGLang PR #29716 HiCacheFile metadata cache](../../raw/crawler/sglang-github-closed-issues-prs/20260708T233633803455Z-github-com-sgl-project-sglang-pull-29716-b6242f612e.md)
- [SGLang PR #30255 DSV4 sparse prefill Triton recompilation](../../raw/crawler/sglang-github-closed-issues-prs/20260708T233633800329Z-github-com-sgl-project-sglang-pull-30255-d5016bf405.md)
- [SGLang PR #30351 KV-transfer fan-out metrics](../../raw/crawler/sglang-github-closed-issues-prs/20260714T234021668233Z-github-com-sgl-project-sglang-pull-30351-df076892cc.md)
- [SGLang PR #30457 DP-attention scheduler receive interval](../../raw/crawler/sglang-github-closed-issues-prs/20260714T234021666327Z-github-com-sgl-project-sglang-pull-30457-59df9d512c.md)
- [SGLang PR #31001 GLM/DeepSeek NVFP4 FlashInfer fix](../../raw/crawler/sglang-github-closed-issues-prs/20260713T234005167501Z-github-com-sgl-project-sglang-pull-31001-8e73a7e57f.md)
- [SGLang July 15 #30355](../../raw/crawler/sglang-github-closed-issues-prs/20260715T234028353201Z-github-com-sgl-project-sglang-pull-30355-31931c5d7d.md)
- [SGLang July 15 #30997](../../raw/crawler/sglang-github-closed-issues-prs/20260715T234028355612Z-github-com-sgl-project-sglang-pull-30997-8fda1aa71b.md)
- [SGLang July 15 #31333](../../raw/crawler/sglang-github-closed-issues-prs/20260715T234028357774Z-github-com-sgl-project-sglang-pull-31333-b47d00a41d.md)
- [SGLang July 15 #31272](../../raw/crawler/sglang-github-closed-issues-prs/20260715T234028379398Z-github-com-sgl-project-sglang-pull-31272-4ddb017271.md)
