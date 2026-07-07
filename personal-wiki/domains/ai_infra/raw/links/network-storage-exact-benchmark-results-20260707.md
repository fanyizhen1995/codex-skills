---
type: RawSource
title: Network Storage Exact Benchmark Result Source Probe
source_kind: web-link-probe-note
url: https://github.com/mlcommons/storage_results_v2.0
related_urls:
  - https://api.github.com/repos/mlcommons/storage_results_v2.0/contents?ref=main
  - https://api.github.com/repos/mlcommons/storage_results_v2.0/contents/closed?ref=main
  - https://api.github.com/repos/mlcommons/storage_results_v2.0/contents/open?ref=main
  - https://mlcommons.org/benchmarks/storage/
captured: 2026-07-07
status: blocked
---
# Source

Bounded source-probe note for the exact network/storage benchmark-result gap in
`ai_infra`.

Primary source family:

- MLCommons Storage v2.0 results repository: https://github.com/mlcommons/storage_results_v2.0
- MLCommons Storage benchmark landing page: https://mlcommons.org/benchmarks/storage/

This task intentionally did not promote any product/provider measured-result
claim. The previous topology/benchmark note already captured MLCommons Storage
as benchmark-method and result-framework evidence. This note records the
additional attempt to select an exact result artifact with measured values.

# Local Duplicate Search

Local search covered `wiki/`, `raw/links/`, `raw/crawler/`, `raw/github/`,
`coverage-map.json`, `loop-state.json`, the r8 network/storage gap proof, and
the r9 hardware gap proof for:

- `MLCommons Storage`
- `storage_results_v2.0`
- `benchmark submission`
- `storage system`
- `workload`
- `backend`
- `compute nodes`
- `accelerator count`
- `networking`
- `throughput`
- `checkpointing`
- `FSx`
- `Lustre`
- `WEKA`
- `Ceph`
- `NVMe-oF`
- `RoCE`
- `EFA`
- `Spectrum-X`
- `OCI`
- `topology`
- `configuration`
- `measured result`
- `duplicate boundary`
- `blocked-source`

Findings:

- Existing local evidence contains MLCommons Storage benchmark-method and
  result-framework facts, not a captured per-submission result file.
- Existing local network/storage evidence already covers EFA, FSx for Lustre,
  WEKA, Ceph, SPDK/NVMe-oF, AWS HyperPod topology/checkpoint mechanics,
  Spectrum-X/RoCE fabric operations, OCI RoCE design, and product-specific
  DPU/NVMe-oF signals.
- No local raw or curated file exposed a complete exact benchmark submission
  with source-backed submitter/provider, workload, backend, storage system,
  compute-node count, accelerator count where present, networking/topology,
  storage configuration, and measured throughput.

# Link Probe

Local shell probes were bounded to the official MLCommons source family:

- `https://api.github.com/repos/mlcommons/storage_results_v2.0/contents?ref=main`
- `https://api.github.com/repos/mlcommons/storage_results_v2.0/contents/closed?ref=main`
- `https://api.github.com/repos/mlcommons/storage_results_v2.0/contents/open?ref=main`
- selected `raw.githubusercontent.com` result-path probes after the GitHub
  result repository had already been identified by the r8 source note.

Result:

- The shell sandbox returned `Temporary failure in name resolution` for GitHub
  API and raw GitHub probes.
- Because exact result-file content was not available in the local corpus and
  could not be fetched through shell link probes, this task records the exact
  benchmark-result gap as blocked rather than inferring result values from the
  repository name, benchmark method, or storage product documentation.

# Captured Boundary

Use this note as blocked-source evidence only:

- It proves the local corpus does not yet contain a complete exact MLCommons
  Storage measured-result artifact.
- It proves this run attempted bounded official-source probes for the exact
  result repository and was blocked by local DNS resolution.
- It does not prove a storage system's throughput, ranking, benchmark
  leadership, or training/checkpoint performance.

# Future Promotion Criteria

A future exact benchmark claim can be promoted only after a specific result
artifact or report is captured and the curated page preserves:

- benchmark version and result artifact path;
- submitter/provider and system type;
- workload and backend;
- storage system and storage/fabric configuration;
- compute-node count and accelerator count where present;
- networking/topology;
- measured throughput or benchmark result value;
- source limitations and any closed/open division boundaries.
