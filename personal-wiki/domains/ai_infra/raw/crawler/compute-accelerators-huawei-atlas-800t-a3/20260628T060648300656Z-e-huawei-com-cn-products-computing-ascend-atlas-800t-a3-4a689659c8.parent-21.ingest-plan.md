# Ingest Plan: Huawei Atlas 800T A3 Aggregate System Fields

## Source

- Raw source: `personal-wiki/domains/ai_infra/raw/crawler/compute-accelerators-huawei-atlas-800t-a3/20260628T060648300656Z-e-huawei-com-cn-products-computing-ascend-atlas-800t-a3-4a689659c8.md`
- Source rank: S1 official Huawei Enterprise product page
- Semantic parent task: parent-21

## Duplicate Check

Existing curated pages already treated Atlas 800T A3 as aggregate comparison evidence, not a normalized structured row. Parent-14 intentionally avoided Atlas 800T A3 while promoting Atlas 300I A2 card variants. Parent-17 promoted an analogous but distinct AWS Trn2 cloud-offering aggregate memory field. No existing SKU row resolves Atlas 800T A3 `cloud_accelerator_count` or `aggregate_memory`.

## Promotion Boundary

Promote only schema-supported aggregate fields:

- `cloud_accelerator_count=8 count` from the source technical table row stating one server has 8 Ascend 910 processors.
- `aggregate_memory=1024 GB` from the source table row stating 8 x 128 GB on-chip memory.

Keep all other source-visible values as boundary or raw comparison evidence:

- 6.0 PFLOPS FP16 and 12.0 POPS INT8 are aggregate system compute values, not single-accelerator fields in the current schema.
- 3.2 TB/s memory bandwidth, 784 GB/s D2D bandwidth, 8 x 400GE RoCE interfaces, 56 x 400GE bus-protocol interfaces, PCIe 5.0 expansion slots, local storage, power, cooling, fans, dimensions, operating-temperature, deployment, benchmark, production-operation, service-SLO, training-throughput, and inference-throughput claims are not normalized in this task.

## Planned Outputs

- `data/compute_accelerators/skus/sample-skus.yaml`
- `data/compute_accelerators/observations/sample-observations.yaml`
- `data/compute_accelerators/resolved/sample-resolved-specs.yaml`
- `wiki/projects/compute-accelerator-spec-catalog.md`
- `wiki/references/compute-accelerator-parameter-comparison.md`
- `wiki/references/ai-infra-coverage-map.md`
- `coverage-map.json`
- `loop-state.json`
- `ingest.md`
- `manifest-ai-infra-expansion-continuation-20260708-parent-21-gap-proof.json`
