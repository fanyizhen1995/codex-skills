# Compute Accelerator Spec Catalog Design

## Goal

Create a maintainable catalog for current and historical compute accelerator
cards and modules across GPU, NPU, TPU, DPU, IPU, FPGA, DSA, and AI ASIC
families. The catalog must provide three connected outputs:

- Structured data for querying, comparison, export, and future API use.
- Curated wiki pages for source policy, field definitions, taxonomy, and
  human-readable summaries.
- Crawler workbench source profiles for ongoing discovery of official and
  high-value source changes.

The design prioritizes field-level provenance over complete initial coverage.
Every important parameter should be traceable to a source, and conflicting
values should be preserved instead of overwritten.

## Scope

The first implementation covers broad compute accelerators used in AI,
networking, storage, cloud infrastructure, and programmable offload:

- `gpu`
- `npu`
- `tpu`
- `dpu`
- `ipu`
- `fpga`
- `dsa`
- `ai_asic`

The first data set is a representative sample, not an exhaustive SKU database.
It should validate the schema, source ranking, candidate extraction, conflict
rules, wiki organization, and crawler profile shape.

## Non-Goals

- Building a complete commercial GPU database in the first version.
- Replacing original vendor documentation or mirroring full datasheets in wiki
  pages.
- Treating benchmark results as theoretical peak specifications.
- Treating cloud instance totals as single-card specifications.
- Automatically resolving values from third-party, media, procurement, or
  analyst sources without review.
- Handling secret or authenticated sources in the first implementation.

## Recommended Approach

Use structured specifications as the primary facts layer. Raw sources and
crawler snapshots feed candidate observations into structured files; curated
wiki pages explain the catalog, source policy, and field glossary.

This avoids three independent systems:

- `raw/` remains the evidence layer.
- `data/compute_accelerators/` becomes the normalized facts layer.
- `wiki/` becomes the durable explanatory layer.
- Crawler profiles become discovery and refresh entry points.

## Repository Layout

Create the structured catalog under the existing `ai_infra` domain:

```text
personal-wiki/domains/ai_infra/data/compute_accelerators/
  README.md
  schema/
    source-ranks.yaml
    accelerator-scopes.yaml
    spec-fields.yaml
  sources/
    source-registry.yaml
  skus/
    sample-skus.yaml
  observations/
    sample-observations.yaml
  resolved/
    sample-resolved-specs.yaml
  candidates/
    README.md
```

Add curated wiki pages under the same domain:

```text
personal-wiki/domains/ai_infra/wiki/references/compute-accelerator-spec-sources.md
personal-wiki/domains/ai_infra/wiki/references/compute-accelerator-field-glossary.md
personal-wiki/domains/ai_infra/wiki/projects/compute-accelerator-spec-catalog.md
personal-wiki/domains/ai_infra/wiki/projects/compute-accelerator-crawler.md
```

Extend crawler profiles in:

```text
personal-wiki/apps/crawler_workbench/config/sources.example.yaml
```

## Data Model

### Vendors

Vendor records identify organizations such as NVIDIA, AMD, Intel, Huawei,
Cambricon, Biren, Enflame, MetaX, Iluvatar, Google, AWS, Microsoft, Alibaba,
Tencent, and other accelerator vendors or cloud providers.

Minimum fields:

- `vendor_id`
- `name`
- `aliases`
- `homepage`
- `vendor_type`

### Product Families

Product family records group related SKUs and modules, such as Hopper,
Blackwell, AMD Instinct MI300, Gaudi, Ascend, Trainium, Inferentia, TPU,
BlueField, Pensando, Alveo, Agilex, and IPU families.

Minimum fields:

- `family_id`
- `vendor_id`
- `name`
- `scope`
- `architecture`
- `source_refs`

### Accelerator SKUs

SKU records represent a concrete card, module, accelerator instance, or
cloud-visible accelerator offering, such as H100 SXM, H100 PCIe, H200 SXM,
B200, GB200, MI300X, MI325X, Gaudi 3 HL-338, Ascend 910B, Cloud TPU v5p,
BlueField-3, Alveo V80, Trainium2, or Inferentia2.

Minimum fields:

- `sku_id`
- `vendor_id`
- `family_id`
- `canonical_name`
- `aliases`
- `scope`
- `form_factor`
- `release_status`
- `source_refs`

### Specification Fields

Field definitions live in `schema/spec-fields.yaml` and define canonical names,
types, units, applicable scopes, and whether a field is theoretical, observed,
cloud-specific, or benchmark-specific.

Fields are grouped into:

- `common_specs`: vendor, SKU, architecture, process, memory, bandwidth,
  power, form factor, host interface, interconnect, software stack, and release
  information.
- `compute_specs`: FP64, FP32, TF32, BF16, FP16, FP8, INT8, TOPS/FLOPS,
  sparse performance, matrix engine details, and supported precision modes.
- `role_specific_specs`: DPU network ports and offloads, FPGA LUT/DSP/BRAM
  resources, TPU pod and MXU details, NPU/DSA compiler and operator support,
  cloud custom accelerator integration details.

The schema must allow sparse records. A DPU should not need GPU tensor
performance fields, and an FPGA should not need TPU pod fields.

### Field Observations

Field observations are the provenance-bearing records. Each observation
captures one source-backed claim about one field on one SKU or offering.

Minimum fields:

- `observation_id`
- `sku_id`
- `field`
- `value`
- `unit`
- `source_id` or `raw_path`
- `source_rank`
- `captured_at`
- `source_locator`
- `is_official`
- `is_inferred`
- `confidence`
- `notes`

Observations are append-friendly. A new datasheet version, cloud document
change, runtime probe, or benchmark result creates a new observation rather
than overwriting prior evidence.

### Resolved Specifications

Resolved specifications provide the best currently accepted value for each
field while preserving the observation that supports the value.

Example shape:

```yaml
sku_id: nvidia-h200-sxm
resolved_fields:
  memory_capacity:
    value: 141
    unit: GB
    source_observation_id: obs-nvidia-h200-product-page-memory
    resolved_by: rule
    confidence: high
    conflict_status: clean
    updated_at: "2026-06-27"
```

Resolved fields may be empty when evidence is weak or conflicting.

### Source Registry

`sources/source-registry.yaml` records source identities and policies:

- `source_id`
- `name`
- `url`
- `source_rank`
- `publisher`
- `source_type`
- `trust_policy`
- `crawl_policy`
- `notes`

The source registry prevents every observation from redefining source metadata.

## Source Ranking

Source ranks combine factual trust and automation policy.

### S1: Original Vendor Official Specifications

Examples: vendor product pages, datasheets, product briefs, official PDFs, and
official support documents from NVIDIA, AMD, Intel, Huawei, Cambricon, Biren,
Enflame, MetaX, Iluvatar, and similar vendors.

Use for core card and module fields such as memory, bandwidth, power, form
factor, interconnect, precision performance, and software support.

Automation policy: raw snapshots may be automatic. Resolved updates may be
automatic only when the field is currently unresolved or the new observation is
a clear same-source version update with no semantic conflict.

### S2: Cloud Provider Official Specifications

Examples: AWS EC2 accelerated instance documentation, Google Cloud GPU/TPU
machine docs, Azure GPU VM sizes, OCI GPU shapes, Alibaba Cloud GPU instances,
Tencent Cloud GPU instances, and Volcano Engine GPU offerings.

Use for cloud offering records, accelerator counts, aggregate memory, network,
local storage, region, instance naming, and SKU mapping.

Automation policy: may update cloud offering fields. Must not overwrite
single-card vendor specifications.

### S3: Standards, Registries, and Benchmark Submissions

Examples: MLCommons/MLPerf, OCP/OAI/OAM, PCI ID databases, SPEC-style result
sets, and official standards documents.

Use for benchmark observations, system configurations, accelerator module
standards, and device identification.

Automation policy: may create observations and benchmark records. Must not
overwrite theoretical peak fields.

### S4: Runtime and Inventory Probe Output

Examples: `nvidia-smi`, NVML, DCGM, CUDA device properties, `amd-smi`, ROCm
SMI, Intel `xpu-smi`, Huawei `npu-smi`, `lspci`, and cluster inventory tools.

Use for observed fields, deployed asset state, driver/firmware versions,
configured power limits, partitions, MIG/SR-IOV state, topology, and runtime
memory reports.

Automation policy: writes observed/runtime fields only. It does not overwrite
official theoretical specifications.

### S5: Third-Party, Media, Procurement, Analyst, and Community Sources

Examples: TechPowerUp, WikiChip, ServeTheHome, AnandTech, vendor launch decks
not hosted as official specs, public procurement documents, analyst reports,
and community-maintained lists.

Use for candidate observations, historical notes, and gap filling when official
data is not public.

Automation policy: default to pending review. S5 observations cannot become
resolved values unless `reviewed_by` is present.

## Crawler Profile Design

Add compute accelerator source profiles to
`personal-wiki/apps/crawler_workbench/config/sources.example.yaml`.

Profiles should cover stable entry points first:

- Vendor official accelerator pages and datasheet indexes.
- Cloud provider accelerator and instance type documentation.
- MLPerf result indexes and OCP/OAM pages.
- PCI ID data or mirrors where appropriate.
- Low-frequency third-party monitoring sources with auto-ingest disabled.

Additional profile fields:

```yaml
source_rank: S1
accelerator_scope:
  - gpu
  - npu
extract_mode: specs_candidate
vendor_hint: nvidia
auto_resolve: false
```

`extract_mode: specs_candidate` means the crawler writes raw snapshots and
candidate structured records. It does not directly edit resolved specs.

## Update Flow

All crawler and manual ingest paths use the same flow:

1. A source profile fetches a page, PDF, API response, RSS entry, or probe
   output and saves a raw snapshot.
2. An extractor writes `candidates/*.yaml` with candidate SKUs, fields, units,
   source references, source rank, and confidence.
3. A normalizer converts units and names to canonical schema values.
4. A resolver compares candidate observations against existing field
   observations.
5. Clean high-trust changes update resolved specs.
6. Conflicting or low-trust changes remain pending with `needs_review`.
7. Curated wiki pages update only navigational summaries, source policy,
   glossary details, and important change notes.
8. Validation checks schema, source refs, wiki links, and crawler profile
   metadata.

## Conflict Rules

- S1 official vendor specifications outrank S2 cloud docs and S5 third-party
  sources for single-card specs.
- For two S1 sources, newer official datasheet or product-page versions win,
  while old observations remain in history.
- Cloud provider aggregate values belong to cloud offering fields and do not
  conflict with single-card fields.
- Runtime probe values belong to observed/runtime fields and do not overwrite
  official theoretical fields.
- Benchmark results belong to benchmark fields and do not overwrite theoretical
  peak performance fields.
- S5-only values remain unresolved unless manually reviewed.
- If units differ but normalize cleanly, the resolver records the canonical
  unit and keeps the original source unit in the observation notes.
- If marketing precision names are ambiguous, the field remains unresolved and
  a note explains the ambiguity.

## Wiki Organization

The wiki should explain the catalog and its limits rather than duplicate all
structured data.

### `compute-accelerator-spec-sources.md`

Documents source ranks, source entry points, trust rules, and when sources can
be auto-resolved.

### `compute-accelerator-field-glossary.md`

Defines field names, units, scope applicability, and common ambiguity such as
peak versus sparse peak, aggregate versus per-card memory, and observed versus
official values.

### `compute-accelerator-spec-catalog.md`

Explains the structured data layout, initial coverage, sample SKUs, how to
query or export the data, and which areas are intentionally incomplete.

### `compute-accelerator-crawler.md`

Documents source profile conventions, extractor output, candidate review, and
auto-resolve boundaries.

Optional future split pages:

```text
wiki/references/nvidia-accelerator-skus.md
wiki/references/amd-accelerator-skus.md
wiki/references/cloud-accelerator-offerings.md
wiki/references/dpu-ipu-fpga-accelerators.md
```

## Initial Sample Coverage

Use 12-18 representative entries to validate the model:

- GPU: NVIDIA H100/H200/B200 or GB200, AMD MI300X/MI325X, Intel Data Center
  GPU Max.
- NPU/AI ASIC: Huawei Ascend 910B or 910C source entries, Cambricon MLU370 or
  MLU590 source entries.
- TPU: Google Cloud TPU v5e, v5p, or v6e documentation entries.
- DPU/IPU: NVIDIA BlueField-3, AMD Pensando, Intel IPU E2000.
- FPGA: AMD/Xilinx Alveo V80 or U55C, Intel Agilex or FPGA PAC.
- DSA/cloud custom: AWS Trainium, Trainium2, Inferentia, Inferentia2, and
  Microsoft Azure Maia as source and candidate entries when public fields are
  limited.

For sources with incomplete public specifications, create source registry and
candidate records without forcing complete resolved specs.

## Validation Rules

The first implementation can use manual review plus lightweight tests, but the
data should be shaped for future CLI validation.

Rules:

- Every SKU must include `vendor_id`, `scope`, `canonical_name`, and
  `source_refs`.
- Every resolved field must reference at least one observation.
- Every observation must reference a source registry entry or raw path.
- Every field unit must be allowed by `schema/spec-fields.yaml`.
- S5 sources cannot auto-resolve unless `reviewed_by` exists.
- Wiki pages must cite data files and source policy pages.
- Crawler profiles must include `source_rank`, `accelerator_scope`,
  `extract_mode`, and `auto_resolve`.
- Accelerator scope values must come from `schema/accelerator-scopes.yaml`.
- Field applicability should be enforced by scope where practical.

## Testing Strategy

Focused implementation tests:

- Parse every schema and sample YAML file.
- Validate that sample SKU scopes exist in `accelerator-scopes.yaml`.
- Validate that sample observation fields exist in `spec-fields.yaml`.
- Validate that sample resolved fields point to existing observations.
- Validate that S5 observations cannot auto-resolve without review metadata.
- Validate that crawler source profiles accept the new metadata fields.
- Run `personal-wiki` index and validation after wiki page changes.

## Error Handling

- Fetch failure: record failed crawl status, keep prior raw snapshot and
  structured data unchanged.
- Extractor ambiguity: write a candidate with `needs_review` and avoid
  resolved updates.
- Unit conversion failure: keep the raw observation, mark normalized field
  unresolved, and record the failed conversion note.
- Source conflict: keep all observations, mark the resolved field as
  `conflict_status: needs_review`.
- Missing public fields: leave resolved fields empty rather than inventing or
  inferring values.
- Dirty worktree during automated update: do not commit automatically.

## Security and Compliance

Only public unauthenticated sources are in scope for the first version. Future
authenticated source profiles must store only non-secret references such as
environment variable names or local credential file paths.

The crawler must not bypass access controls, paywalls, anti-crawling systems,
or license restrictions. Raw snapshots should be source evidence for personal
knowledge management, not redistributed vendor documentation.

## Implementation Phases

### Phase 1: Spec and Seed Data

Create schema files, source ranks, accelerator scopes, sample source registry,
sample SKU records, sample observations, sample resolved specs, and candidate
README.

### Phase 2: Wiki Pages

Create the four curated wiki pages, update the domain index, and run
`personal-wiki` validation.

### Phase 3: Crawler Profiles

Add source profiles for representative vendor, cloud, standard, and third-party
entry points. Validate the crawler profile parser accepts the new metadata.

### Phase 4: Validation Helpers

Add lightweight validation tests or CLI helpers for data consistency, source
rank policy, scope/field compatibility, and resolved observation references.

### Phase 5: Expansion

Add more vendors and SKUs incrementally. Each expansion should add raw/source
evidence, observations, resolved values only when justified, and wiki notes only
when they add reusable context.

## Open Questions

- Whether the structured files should remain YAML long term or move into
  SQLite-backed crawler workbench tables after the seed model stabilizes.
- Whether runtime probe ingestion should be part of this catalog or a separate
  inventory domain that links back to accelerator SKU definitions.
- Whether cloud custom chips such as TPU, Trainium, Inferentia, and Maia should
  share the same SKU object type as cards/modules or use a distinct `offering`
  subtype for non-card deployments.
