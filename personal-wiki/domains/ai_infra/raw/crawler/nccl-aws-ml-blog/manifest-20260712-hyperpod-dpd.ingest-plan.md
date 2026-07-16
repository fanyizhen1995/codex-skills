# Ingest Plan

Source path: `raw/crawler/nccl-aws-ml-blog/manifest-20260712-hyperpod-dpd.json`

## Durable Claims

- The July 12 local AWS ML Blog capture is a new local URL identity for SageMaker HyperPod Disaggregated Prefill and Decode (DPD), not a duplicate of existing vLLM, PegaFlow, SGLang disaggregated-prefill, EFA, or HyperPod training-topology coverage.
- The source describes DPD as separating prefill and decode across GPU pools. Short prompts below `routingThreshold` bypass prefill and run on a decoder, while long prompts route through a prefiller and then a decoder.
- The implementation stack is source-described as the vLLM Production Stack router plus LMCache, `LMCacheConnectorV1`, LMCache PD, NIXL, `libfabric`, and EFA GPU-Direct RDMA for KV cache movement.
- HyperPod Inference Operator v3.2 or later and `InferenceEndpointConfig.spec.pdSpec` are the operator/API boundary. The presence of `pdSpec` makes the endpoint disaggregated, creates separate prefill and decode `Deployment` objects, and wires them through the router and LMCache PD backend.
- DPD deployment boundaries include at least one prefill node and one decode node, RDMA-capable EFA, p5/p6 instance families, same-AZ EFA placement, NVLink requirements, DPD worker images that include vLLM, LMCache, NIXL, and the EFA `libfabric` provider, and checkpoint loading from S3, FSx, HuggingFace, or instance NVMe.
- Scaling guidance is source-scoped: DPD currently supports one decoder replica with multiple prefiller replicas, starts from a 1:1 prefill-to-decode ratio, may use 2:1 or 3:1 ratios for prefill-heavy workloads, uses `kvaware` or `session` routing for locality, and may adjust `PD_BUFFER_SIZE`, `max-model-len`, or concurrency when decode is saturated.
- The benchmark section is AWS-stated context only: `genai-bench`, fixed 4096 input and 256 output tokens, concurrency 8/16/32, one prefiller and one decoder across two nodes, KV-aware routing, eager prefill, decoder CUDA graphs, single-node colocated baseline, `ml.p5.48xlarge` H100 and `ml.p5en.48xlarge` H200 settings, and AWS-stated TPOT, throughput, E2E latency, and TTFT tradeoffs.
- Observability support is limited to source-stated HyperPod Inference dashboard, Tasks dashboard CPU/GPU usage, and Cluster Overview dashboard surfaces. The capture does not provide alert thresholds, SLO definitions, production incidents, or postmortem evidence.

## Target Pages

- Update `wiki/references/inference-runtime-infrastructure.md` with a bounded SageMaker HyperPod DPD section covering router behavior, `routingThreshold`, LMCache/vLLM/NIXL stack, scaling guidance, and AWS-stated benchmark context.
- Update `wiki/references/network-storage-cluster-infrastructure.md` with EFA/libfabric/GPU-Direct RDMA KV-transfer and same-AZ p5/p6 deployment boundaries.
- Update `wiki/references/orchestration-scheduling-infrastructure.md` with HyperPod Inference Operator v3.2, `InferenceEndpointConfig.spec.pdSpec`, prefill/decode/router deployment, pod/container, per-role resources, and checkpoint loading boundaries.
- Update `wiki/references/ai-infra-coverage-map.md`, `coverage-map.json`, `loop-state.json`, and `ingest.md` so semantic parent-26 is discoverable.

## Non-Goals

- Do not fetch AWS docs, GitHub repositories, or external pages.
- Do not ingest the adjacent July 12 AWS Nemotron customization capture, AWS AgentCore MCP capture, NCCL GitHub releases, NCCL GitHub issues, NVIDIA GQE/Presto captures, or vLLM blog refreshes.
- Do not treat AWS blog benchmark percentages or latency/throughput claims as local results, MLCommons submissions, product rankings, production SLOs, alert thresholds, or generalized performance guarantees.
- Do not claim KServe autoscaling/canary behavior, SGLang shipped fixes, exact MLCommons result coverage, production postmortems, or end-to-end RAG propagation proof.
- Do not create product catalog rows, accelerator SKU fields, or resolved hardware entries from this source.
- Do not modify crawler backend/frontend, Loop Dashboard, harness code, dependencies, generated files, runtime logs, secrets, or unrelated dirty paths.

## Compact Decision

The raw AWS ML Blog capture is readable and small enough to inspect directly. Keep it as Markdown under `raw/crawler/nccl-aws-ml-blog/`; no gzip compaction is needed.
