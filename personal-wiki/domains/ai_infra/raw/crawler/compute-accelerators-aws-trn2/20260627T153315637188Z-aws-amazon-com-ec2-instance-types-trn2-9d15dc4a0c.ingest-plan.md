---
type: IngestPlan
domain: ai_infra
source: 20260627T153315637188Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md
status: done
created_at: 2026-07-09T18:10:18Z
task_id: ai-infra-expansion-continuation-20260708-parent-17
---

# AWS Trn2 Aggregate Memory Ingest Plan

## Source Boundary

- Raw source: `personal-wiki/domains/ai_infra/raw/crawler/compute-accelerators-aws-trn2/20260627T153315637188Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md`
- Source type: existing local official AWS cloud offering capture.
- Scope: Amazon EC2 Trn2 `trn2.48xlarge` and `trn2u.48xlarge` cloud offering rows.

## Promotion

- Reuse the existing `aws-trainium2-trn2-offering` SKU.
- Add one `aggregate_memory` observation for the source-visible Trn2 instance accelerator memory.
- Resolve `1.5 TB` accelerator memory as `1536 GB` because the catalog field uses GB and binary cloud memory convention is already used for the product details table.
- Keep the existing `cloud_accelerator_count=16` resolved value unchanged.

## Boundaries

- Do not promote UltraServer `6 TB` as a structured row in this task; keep it as raw comparison evidence because the existing catalog row represents Trn2 instance offerings.
- Do not promote aggregate FP8 PFLOPS, total memory bandwidth, EFAv3 bandwidth, local NVMe storage, vCPU count, host memory, price-performance, energy-efficiency, model-count, service-integration, testimonial, availability, or production-operation wording into structured accelerator fields.
- Do not create new external captures, crawler subscriptions, or Domain Channels.

## Outputs

- `data/compute_accelerators/observations/sample-observations.yaml`
- `data/compute_accelerators/resolved/sample-resolved-specs.yaml`
- `wiki/projects/compute-accelerator-spec-catalog.md`
- `wiki/references/compute-accelerator-parameter-comparison.md`
- `wiki/references/ai-infra-coverage-map.md`
- `coverage-map.json`
- `loop-state.json`
- Parent-17 gap proof and verification manifests.
