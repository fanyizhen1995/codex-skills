# Ingest Plan

Source path: `raw/crawler/nccl-github-closed-issues/manifest-20260711-20260714-nccl-gin-cutedsl.json`

## Durable Claims

- The July 11 and July 14 NCCL GitHub closed-issue page captures contain two new page-level supplement identities after the June joined API/comment corpus and the July 1/3 supplement: `github:nvidia/nccl#2246` and `github:nvidia/nccl#1957`.
- Issue #2246 is a CuTeDSL NCCL device-API question/report. The page-visible issue body says a host-created `ncclDevComm` pointer was passed as a raw 64-bit value into an H20 kernel and the first device-side `dev_comm.lsa_rank` field dereference failed with `cudaErrorIllegalAddress`.
- Issue #1957 is a GIN GDAKI mode report. The page-visible issue body says `gin_alltoall_pure` hung with a 1500 MTU NIC and the reporter observed hard-coded 4K MTU behavior in `doca modify qp` / `doca modify QP` context.
- Existing NCCL curated coverage already includes the joined closed-issue API/comment corpus through the June 2026 cutoff, the July 1/3 scheduled supplement for #2226 and #2024, NCCL release-note GIN terminology, and parent-25 arXiv abstract refresh evidence. It did not curate #2246 or #1957 before this task.

## Target Pages

- Update `wiki/references/nccl-github-closed-issues.md` with the July 11/14 supplement manifest, page-level scope, and a concise issue table for #2246 and #1957.
- Update `wiki/references/nccl-release-notes.md` only to clarify that #1957 is issue-level GIN/GDAKI field evidence adjacent to release-note GIN terminology, not a release-note entry.
- Update `wiki/projects/nccl.md` so NCCL's operational issue evidence mentions the July GIN and CuTeDSL supplement.
- Update `wiki/references/ai-infra-coverage-map.md`, `coverage-map.json`, `loop-state.json`, and `ingest.md` so semantic parent-28 is discoverable.

## Non-Goals

- Do not fetch external pages, GitHub comments, repository issue API pages, DOCA source pages, maintainer replies, or release pages.
- Do not treat #2246 or #1957 as confirmed NVIDIA root cause, product fix, release-note guarantee, benchmark result, production postmortem, service SLO, or general platform compatibility rule.
- Do not update accelerator structured data, source registry rows, benchmark rows, hardware catalog pages, crawler backend/frontend, Loop Dashboard, loop supervisor, harness code, package files, or unrelated docs.

## Compact Decision

The two raw Markdown issue captures are small and useful for direct inspection. Keep them readable under `raw/crawler/nccl-github-closed-issues/`; no gzip compaction is needed.
