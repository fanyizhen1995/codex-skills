# Ingest Plan

Source path: `raw/crawler/nccl-nvidia-blog-wide/20260705T041056438015Z-developer-nvidia-com-blog-designing-gpu-accelerated-query-engines-with-nvidia-gqe-ae88d57da8.md`

## Durable Claims

- The July 5 local NVIDIA Developer Blog capture is a new local URL identity for NVIDIA GQE, a GPU Query Engine reference architecture for large-scale SQL query execution on modern NVIDIA hardware.
- GQE's query layer accepts Substrait plans, with the source describing Apache DataFusion transforming SQL into Substrait before GQE consumes the optimized logical plan and produces a physical plan.
- The data layer abstracts GPU memory, CPU memory, and disk readers; the promoted slice focuses only on the source's in-memory CPU layout where row groups and partitions are transferred to the GPU on demand and assembled into cuDF-native columns.
- The execution layer uses a task graph with relational operators built on NVIDIA cuDF and CUDA-X dependencies including CCCL, nvCOMP, and nvSHMEM.
- The data-path optimizations are CPU-to-GPU movement, compressed transfers, GPU decompression, and partition pruning: nvCOMP compression/decompression, Blackwell Decompression Engine offload for LZ77-family formats, Cascaded-vs-LZ4 per-column selection heuristics, zone-map pruning, and batched `cudaMemcpyBatchAsync` partition transfer.
- The source-stated benchmark context is TPC-H SF1000 / 1 TB on a GB200 NVL4 server using one B200 GPU connected to Grace CPU by NVLink-C2C, compared to DuckDB 1.4.1 on a Turin EPYC 9755 CPU. The source reports 9.0 s total GQE runtime, 74.0 s single-socket DuckDB, 70.6 s dual-socket DuckDB, 7.5x aggregate speedup, and up to 25.5x per-query gains, but explicitly says the results are not comparable to published TPC-H results because they do not comply with the TPC-H specification.

## Duplicate And Refresh Boundaries

- Existing curated data/RAG pages covered Ray Data, Flink, Kafka, Airflow, Dagster, Prefect, TEI, DataHub/OpenLineage, table formats, vector stores, Azure AI Search, Langfuse, and an AgentCore MCP DynamoDB data-boundary example. They did not cover GPU query-engine CPU-to-GPU transfer orchestration, compressed transfers, partition pruning, Substrait/DataFusion plan ingestion, cuDF/nvCOMP/nvSHMEM execution dependencies, or GQE benchmark context.
- Existing inference-runtime, network/storage, and compute-accelerator pages contain adjacent GPU runtime, KV-transfer, fabric, and hardware evidence, but no GQE query-engine data infrastructure entry.
- The untracked July 12 GQE refresh differs from the July 5 article body only by an added `featured` tag at the article tail after capture metadata is ignored. Treat it as a duplicate refresh and leave it unstaged unless a later task needs refresh bookkeeping.

## Target Pages

- Update `wiki/references/data-rag-pipeline-infrastructure.md` with a bounded GQE data-path section under data infrastructure, explicitly not a RAG propagation proof.
- Update `wiki/references/ai-infra-coverage-map.md`, `coverage-map.json`, `loop-state.json`, and `ingest.md` so this source is visible to planner/evaluator/search surfaces.
- Create task gap-proof and verification manifests for this run.

## Non-Goals

- Do not fetch external sources or use the July 12 duplicate refresh as a promoted source.
- Do not promote GQE performance numbers as independent benchmarks, product rankings, production SLOs, MLCommons results, or locally reproduced measurements.
- Do not add structured compute-accelerator catalog rows or hardware SKU fields.
- Do not ingest adjacent AWS Nemotron, NCCL release, NCCL GitHub issue, vLLM, SGLang, or other untracked raw backlog.
- Do not modify crawler, harness, frontend, dashboard, Tailnet, or service process code.

## Compact Decision

The raw NVIDIA blog capture is small and readable. Keep it as Markdown under `raw/crawler/nccl-nvidia-blog-wide/`; no gzip compaction is needed.
