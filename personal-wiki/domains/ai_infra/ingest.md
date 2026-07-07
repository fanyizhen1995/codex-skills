# Ingest Log

## Pending

No pending ingest.

## In Progress

No active ingest.

## Done

- [x] `raw/github/{kubernetes-kubernetes-closed-issues,volcano-sh-volcano-closed-issues,kubernetes-sigs-kueue-closed-issues}/` -> `wiki/projects/kubernetes.md`, `wiki/projects/volcano.md`, `wiki/projects/kueue.md`, `wiki/references/kubernetes-volcano-kueue-github-closed-issues.md`
  - Replaced the initial public-API seed with a verified authenticated backfill: `volcano-sh/volcano` all-time closed issues, `kubernetes-sigs/kueue` all-time closed issues, and `kubernetes/kubernetes` issues closed on or after 2023-07-01. The closed-issue sets are in scope, but repository-level comment joins are marked incomplete against GitHub issue comment counters. The combined manifest is `.codex/github-closed-issues/github-closed-issues-volcano-kueue-full-k8s-3y-01/manifest.json`; monthly source profiles are configured for future synchronization with `GITHUB_TOKEN`.
- [x] `raw/links/docs-nvidia-com-deeplearning-nccl-release-notes-index-html.md` -> `wiki/projects/nccl.md`, `wiki/references/nccl-release-notes.md`
  - Captured all 63 per-version release-note pages linked from the official NVIDIA index under `raw/links/`.
- [x] `raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-with-comments.json.gz` -> `wiki/projects/nccl.md`, `wiki/references/nccl-github-closed-issues.md`
  - Captured all closed GitHub issue pages and all repository issue-comment pages, then filtered out pull requests and joined comments for the 1,589 closed issues.
- [x] `raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-with-comments.split-manifest.json` -> `wiki/projects/sglang.md`, `wiki/references/sglang-github-closed-issues-prs.md`
  - Captured closed GitHub issues, closed pull requests, issue/PR timeline comments, PR review comments, updated-order comment segments, and per-item comment supplement pages for the `sgl-project/sglang` repository.
- [x] `raw/crawler/sglang-github-closed-issues-prs/manifest.json` -> `wiki/references/sglang-github-closed-issues-prs.md`
  - Organized 51 selective GitHub page-level crawler snapshots captured on 2026-06-29 as a supplement to the SGLang API corpus. The supplement has 7 issue pages, 44 pull request pages, 10 overlaps with the API corpus, and 41 later selected page captures; it is not a full API corpus refresh.
- [x] `raw/crawler/compute-*` -> `wiki/references/compute-accelerator-crawl-inventory.md`, `wiki/references/compute-accelerator-parameter-comparison.md`
  - Organized compute accelerator discovery and one-shot specification captures covering GPU, NPU, TPU, DPU, IPU, FPGA, DSA, and AI ASIC source profiles. The inventory page records the raw evidence set; the parameter comparison page keeps only source-backed fields that are visible in local raw evidence.
- [x] `raw/crawler/compute-accelerators-intel-dsa/20260629T055534032914Z-www-intel-com-content-www-us-en-content-details-671116-intel-data-streaming-accelerator-ar-5bd93e0cd0.md`, `raw/crawler/compute-accelerator-discovery-nvidia-products/20260628T055950730327Z-www-nvidia-com-en-us-data-center-products-200b75abd8.md`, `raw/crawler/compute-accelerator-discovery-huawei-ascend/20260628T055950888440Z-e-huawei-com-cn-products-computing-ascend-7c96297956.md` -> `wiki/references/compute-accelerator-crawl-inventory.md`
  - Reconciled older pending ingest-plan entries after confirming each raw path is already cited by the compute accelerator crawl inventory. These entries are discovery/source-evidence records, not separate standalone wiki topics.
- [x] `raw/crawler/manual-url-arxiv-org-pdf-2606-24937-02f2168fd4/20260630T012708593204Z-arxiv-org-pdf-2606-24937-9d7a5b6fec.md` -> `wiki/papers/hitchhikers-guide-agentic-ai.md`
  - Organized the arXiv PDF capture as a paper-level reference for LLM systems, agent orchestration, MCP/A2A, and agentic evaluation topics.
- [x] `raw/crawler/sglang-github-closed-issues-prs/manifest-20260701-20260704.json` -> `wiki/references/sglang-github-closed-issues-prs.md`
  - Organized daily scheduled crawler snapshots captured 2026-07-01 through 2026-07-04 as a page-level supplement after the API corpus cutoff: 318 Markdown captures, 41 issues, 277 pull requests, and 198 merged pull requests. The supplement is not a full API corpus refresh with comments or review comments.
- [x] `raw/crawler/nccl-github-closed-issues/manifest-20260701-20260703.json` -> `wiki/references/nccl-github-closed-issues.md`
  - Organized daily scheduled crawler snapshots for NCCL issue #2226 and #2024 as page-level discovery leads after the 2026-06-24 API corpus cutoff.
- [x] `raw/crawler/nccl-technical-blog/` -> `wiki/references/nccl-technical-blog-network-observability.md`, `wiki/projects/nccl.md`, `wiki/references/ai-infra-coverage-map.md`
  - Organized existing local NVIDIA technical-blog captures for NCCL Inspector/Prometheus, communication observability, NCCL 2.24 RAS/NIC Fusion, dynamic communicators, Spectrum-X/RoCE fabric telemetry and convergence, NVBandwidth, SHARP, and NCCL 2.22 cost-estimation evidence. The overlapping `raw/crawler/nccl-nvidia-blog-wide/` Inspector and NVBandwidth captures were treated as duplicate local evidence and were not promoted as separate curated sources.
- [x] `raw/links/{milvus-architecture-overview-20260707,qdrant-indexing-official-docs-20260707,weaviate-vector-indexing-official-docs-20260707,pgvector-readme-official-20260707,faiss-readme-and-indexes-official-20260707}.md` -> `wiki/references/data-rag-vector-infrastructure.md`, `wiki/references/ai-infra-coverage-map.md`
  - Captured concise official primary-source notes for vector database and retrieval infrastructure after confirming no existing dedicated Milvus, Qdrant, Weaviate, pgvector, FAISS, embedding-pipeline, or data/RAG corpus was curated locally. The page covers vector database architecture, HNSW/IVFFlat/IVF/PQ index tradeoffs, filtered retrieval, sparse retrieval, memory/on-disk index placement, and embedding-index lifecycle. The pre-existing untracked 20260706 compute accelerator captures remain out of scope.
- [x] `raw/links/{vllm-readme-official-20260707,tensorrt-llm-kv-cache-official-docs-20260707,triton-inference-server-batcher-official-docs-20260707,llama-cpp-server-official-docs-20260707,onnx-runtime-genai-config-official-docs-20260707}.md`, `raw/crawler/nccl-vllm-blog/`, `raw/crawler/nccl-technical-blog/20260626T015704292802Z-developer-nvidia-com-blog-scaling-ai-inference-across-multiple-gpus-using-nvidia-tensorrt-6fabda0844.md` -> `wiki/references/inference-runtime-infrastructure.md`, `wiki/references/ai-infra-coverage-map.md`
  - Captured concise official primary-source notes and reused existing local vLLM/TensorRT captures after confirming no dedicated curated vLLM, TensorRT-LLM, Triton Inference Server, llama.cpp, or ONNX Runtime GenAI reference page existed. The page covers serving scheduler surfaces, KV-cache lifecycle, model repository/config loading, OpenAI-compatible serving, distributed execution knobs, and local runtime/provider boundaries. The duplicate TensorRT capture under `raw/crawler/nccl-nvidia-blog-wide/` and the pre-existing untracked 20260706 compute accelerator captures remain out of scope.

## Rejected

No rejected sources.
