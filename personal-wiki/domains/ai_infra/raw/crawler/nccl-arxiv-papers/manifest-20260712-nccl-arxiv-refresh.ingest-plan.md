# Ingest Plan

Source path: `raw/crawler/nccl-arxiv-papers/manifest-20260712-nccl-arxiv-refresh.json`

## Durable claims

- The July 12 NCCL arXiv refresh contains three local abstract snapshots: CTA-Pipelining `2607.07862v1`, Adaptive Space-efficient Collectives `2607.04676v1`, and DynamiQ `2602.08923v3`.
- Duplicate reconciliation finds two new unversioned arXiv identities, `arxiv:2607.07862` and `arxiv:2607.04676`, and one version refresh, `arxiv:2602.08923`, whose v1 abstract was already represented in the July 5 NCCL Arxiv Papers page.
- The existing curated NCCL Arxiv Papers page only indexed the July 5 scheduled batch before this task. CTA-Pipelining and Adaptive Space-efficient Collectives were absent from curated text; DynamiQ was represented by the older v1 capture.
- CTA-Pipelining is useful as abstract-level inference-runtime discovery evidence because the abstract frames latency-oriented multi-GPU spatial scaling for LLM serving on 8-GPU H200 and B200 systems using CUTLASS, cuBLAS, and NCCL, with source-stated latency reductions.
- Adaptive Space-efficient Collectives is useful as abstract-level distributed-training and collective-communication discovery evidence because the abstract describes sparse all-gather, reduce-scatter, and all-reduce algorithms, a bitvector-based Pici format, and source-stated speedups over NCCL at 99% input sparsity.
- DynamiQ v3 is useful as a refresh of an existing gradient-synchronization discovery lead because the abstract keeps the compressed multi-hop all-reduce framing, PyTorch DDP over NCCL P2P boundary, and source-stated improvement and near-baseline accuracy boundaries.

## Target pages

- Update `wiki/references/nccl-arxiv-papers.md` with July 12 refresh scope, duplicate/gap proof, new CTA-Pipelining and Adaptive rows, and a DynamiQ v3 refresh note.
- Update `wiki/projects/nccl.md` so NCCL points to the July 12 arXiv refresh as discovery evidence only.
- Update `wiki/references/distributed-training-infrastructure.md` with bounded abstract discovery notes for Adaptive Space-efficient Collectives and DynamiQ v3.
- Update `wiki/references/inference-runtime-infrastructure.md` with bounded abstract discovery notes for CTA-Pipelining.
- Update `wiki/references/ai-infra-coverage-map.md`, `coverage-map.json`, `loop-state.json`, and `ingest.md` so parent-25 is discoverable.

## Non-goals

- Do not create dedicated paper pages; the generator did not read full papers.
- Do not fetch arXiv PDFs or external source pages.
- Do not promote abstract-stated numbers as reproduced benchmarks, local baselines, production SLOs, product rankings, or implementation guidance.
- Do not change NCCL release-note, GitHub issue, technical-blog, accelerator catalog, crawler profile, backend, frontend, dashboard, package, or harness code.

## Compact decision

The three raw abstract captures are small and useful for direct inspection. Keep them readable in `raw/crawler/nccl-arxiv-papers/`; no gzip compaction is needed.
