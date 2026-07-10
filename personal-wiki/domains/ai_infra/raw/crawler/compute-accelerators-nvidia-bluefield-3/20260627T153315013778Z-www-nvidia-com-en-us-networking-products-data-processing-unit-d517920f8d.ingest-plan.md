---
type: IngestPlan
domain: ai_infra
source: 20260627T153315013778Z-www-nvidia-com-en-us-networking-products-data-processing-unit-d517920f8d.md
status: done
created_at: 2026-07-10T04:28:36Z
task_id: ai-infra-expansion-continuation-20260708-parent-18
---

# NVIDIA BlueField-4 DPU Platform Ingest Plan

## Source Boundary

- Raw source: `personal-wiki/domains/ai_infra/raw/crawler/compute-accelerators-nvidia-bluefield-3/20260627T153315013778Z-www-nvidia-com-en-us-networking-products-data-processing-unit-d517920f8d.md`
- Source type: existing local official NVIDIA BlueField platform capture.
- Scope: BlueField-4 DPU portfolio entry on the BlueField platform page; BlueField-3 remains the pre-existing comparison row.

## Promotion

- Add a distinct `nvidia-bluefield-4-dpu` SKU.
- Add one `network_bandwidth` observation for the source-visible BlueField-4 DPU `800Gb/s infrastructure platform` wording.
- Resolve `network_bandwidth=800 Gb/s` on the BlueField-4 DPU row.
- Preserve the existing `nvidia-bluefield-3-dpu` row and its resolved 400 Gb/s network bandwidth unchanged.

## Boundaries

- Do not promote BlueField-4 STX, Vera CPU, NVIDIA CMX, context-memory storage, cybersecurity, threat-detection, validated-design, ecosystem, benchmark, production-operation, service-SLO, power-efficiency, storage throughput, host-interface, memory, or compute wording into structured catalog fields.
- Keep accelerated storage, NVMe-oF, GPUDirect Storage, block/file/object support, rapid data access, and high-performance inference as curated boundary context only.
- Do not create new external captures, crawler subscriptions, or Domain Channels.

## Outputs

- `data/compute_accelerators/sources/source-registry.yaml`
- `data/compute_accelerators/skus/sample-skus.yaml`
- `data/compute_accelerators/observations/sample-observations.yaml`
- `data/compute_accelerators/resolved/sample-resolved-specs.yaml`
- `wiki/projects/compute-accelerator-spec-catalog.md`
- `wiki/references/compute-accelerator-parameter-comparison.md`
- `wiki/references/network-storage-cluster-infrastructure.md`
- `wiki/references/security-governance-cost-infrastructure.md`
- `wiki/references/ai-infra-coverage-map.md`
- `coverage-map.json`
- `loop-state.json`
- Parent-18 gap proof and verification manifests.
