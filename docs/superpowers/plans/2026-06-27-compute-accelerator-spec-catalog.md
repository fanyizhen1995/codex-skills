# Compute Accelerator Spec Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first validated compute accelerator catalog for GPU, NPU, TPU, DPU, IPU, FPGA, DSA, and AI ASIC specifications with structured YAML data, curated wiki documentation, crawler source profiles, and validation checks.

**Architecture:** Keep raw evidence and curated wiki pages in `personal-wiki/domains/ai_infra`, add a structured YAML facts layer under `data/compute_accelerators`, and add a lightweight wiki CLI validator for catalog consistency. Extend crawler source profile metadata so source discovery can produce candidate spec records without directly resolving final values.

**Tech Stack:** Markdown, YAML, Python standard library, PyYAML, pytest, existing `personal-wiki` CLI, existing FastAPI crawler workbench profile loader.

---

## Pre-Flight

The current worktree may contain unrelated changes such as `hami-gpu-flow-task-lifecycle/`, `.mindfs/`, `.superpowers/`, `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/CONVENTIONS.md`, `docs/QUALITY.md`, `docs/TECH_DECISIONS.md`, `docs/exec-plans/`, `harness-step4-evaluator-gates/`, `tasks.json`, and `progress.md`. Do not revert, stage, or commit those files unless the user explicitly asks.

Before execution, run:

```bash
git status --short
```

Expected: unrelated dirty files may be present. Every commit in this plan must stage only files named in that task.

## File Structure

Create structured catalog files:

- `personal-wiki/domains/ai_infra/data/compute_accelerators/README.md`: catalog purpose, layout, update policy, validation commands.
- `personal-wiki/domains/ai_infra/data/compute_accelerators/schema/source-ranks.yaml`: S1-S5 trust and automation policy definitions.
- `personal-wiki/domains/ai_infra/data/compute_accelerators/schema/accelerator-scopes.yaml`: allowed accelerator scopes and scope descriptions.
- `personal-wiki/domains/ai_infra/data/compute_accelerators/schema/spec-fields.yaml`: canonical field definitions, units, applicability, and field class.
- `personal-wiki/domains/ai_infra/data/compute_accelerators/sources/source-registry.yaml`: seed source registry for representative official, cloud, standard, runtime, and third-party sources.
- `personal-wiki/domains/ai_infra/data/compute_accelerators/skus/sample-skus.yaml`: representative sample SKU and offering records.
- `personal-wiki/domains/ai_infra/data/compute_accelerators/observations/sample-observations.yaml`: field-level observations with source provenance.
- `personal-wiki/domains/ai_infra/data/compute_accelerators/resolved/sample-resolved-specs.yaml`: resolved sample specs pointing back to observations.
- `personal-wiki/domains/ai_infra/data/compute_accelerators/candidates/README.md`: candidate extraction contract.

Create structured catalog validator:

- `personal-wiki/tools/wiki_cli/accelerator_catalog.py`: validate accelerator YAML references, source ranks, scopes, fields, units, and S5 auto-resolve policy.
- Modify `personal-wiki/tools/wiki_cli/cli.py`: add `validate-accelerators` command.
- Test `personal-wiki/tests/test_accelerator_catalog.py`: unit and CLI tests for the accelerator catalog validator.

Create curated wiki pages:

- `personal-wiki/domains/ai_infra/wiki/references/compute-accelerator-spec-sources.md`: source ranking and source entry points.
- `personal-wiki/domains/ai_infra/wiki/references/compute-accelerator-field-glossary.md`: field names, units, and scope applicability.
- `personal-wiki/domains/ai_infra/wiki/projects/compute-accelerator-spec-catalog.md`: catalog overview and structured data guide.
- `personal-wiki/domains/ai_infra/wiki/projects/compute-accelerator-crawler.md`: crawler profile conventions and candidate flow.
- Modify generated `personal-wiki/domains/ai_infra/wiki/index.md` by running the existing index command after adding pages.

Extend crawler profile metadata:

- Modify `personal-wiki/apps/crawler_workbench/config/sources.example.yaml`: append compute accelerator source profiles.
- Modify `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/profiles.py`: validate optional accelerator metadata and persist it in `config_json`.
- Modify `personal-wiki/apps/crawler_workbench/backend/tests/test_db_profiles.py`: add tests for valid and invalid accelerator metadata.

## Task 1: Seed Schema and Source Registry

**Files:**
- Create: `personal-wiki/domains/ai_infra/data/compute_accelerators/README.md`
- Create: `personal-wiki/domains/ai_infra/data/compute_accelerators/schema/source-ranks.yaml`
- Create: `personal-wiki/domains/ai_infra/data/compute_accelerators/schema/accelerator-scopes.yaml`
- Create: `personal-wiki/domains/ai_infra/data/compute_accelerators/schema/spec-fields.yaml`
- Create: `personal-wiki/domains/ai_infra/data/compute_accelerators/sources/source-registry.yaml`

- [ ] **Step 1: Create the catalog README**

Create `personal-wiki/domains/ai_infra/data/compute_accelerators/README.md` with:

```markdown
# Compute Accelerators Data Catalog

This directory stores structured, source-backed accelerator specifications for
the `ai_infra` personal-wiki domain.

`raw/` remains the evidence layer, `data/compute_accelerators/` is the
normalized facts layer, and `wiki/` is the curated explanatory layer.

## Layout

- `schema/`: source ranks, accelerator scopes, and field definitions.
- `sources/`: source registry entries shared by observations and crawler
  profiles.
- `skus/`: representative accelerator card, module, chip, and cloud offering
  records.
- `observations/`: source-backed field observations.
- `resolved/`: accepted values that point back to observations.
- `candidates/`: extractor output waiting for review or resolution.

## Update Policy

- Preserve field-level provenance for important parameters.
- Add a new observation when a source changes; do not overwrite evidence.
- Use resolved values only when a source rank policy allows resolution.
- Keep cloud offering aggregate fields separate from single-card fields.
- Keep runtime probe fields separate from official theoretical specs.
- Do not auto-resolve S5 sources unless a reviewer is recorded.

## Validation

Run the structured catalog validator:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators
```

Run the normal wiki validator after curated page edits:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra
```
```

- [ ] **Step 2: Create source rank schema**

Create `personal-wiki/domains/ai_infra/data/compute_accelerators/schema/source-ranks.yaml` with:

```yaml
source_ranks:
  S1:
    name: Original vendor official specifications
    trust_level: highest
    auto_resolve_allowed: conditional
    description: Vendor product pages, datasheets, product briefs, official PDFs, and support documents.
    allowed_for:
      - official_single_accelerator_specs
      - official_module_specs
      - official_software_support
    restrictions:
      - Resolve automatically only when the field is unresolved or a same-source version update has no semantic conflict.
  S2:
    name: Cloud provider official specifications
    trust_level: high
    auto_resolve_allowed: cloud_offering_only
    description: Official cloud instance, shape, accelerator, and TPU documentation.
    allowed_for:
      - cloud_offering_specs
      - accelerator_count
      - aggregate_memory
      - networking
      - region_availability
    restrictions:
      - Do not overwrite single-card vendor specifications.
  S3:
    name: Standards, registries, and benchmark submissions
    trust_level: medium_high
    auto_resolve_allowed: benchmark_or_registry_only
    description: MLCommons, OCP, PCI ID, and standards or benchmark submissions.
    allowed_for:
      - benchmark_results
      - module_standards
      - device_identification
      - submitted_system_configurations
    restrictions:
      - Do not overwrite theoretical peak specifications.
  S4:
    name: Runtime and inventory probe output
    trust_level: observed
    auto_resolve_allowed: observed_fields_only
    description: nvidia-smi, NVML, DCGM, amd-smi, xpu-smi, npu-smi, lspci, and inventory tools.
    allowed_for:
      - observed_runtime_fields
      - deployed_asset_state
      - driver_firmware_versions
      - configured_power_limits
    restrictions:
      - Do not overwrite official theoretical specifications.
  S5:
    name: Third-party, media, procurement, analyst, and community sources
    trust_level: review_required
    auto_resolve_allowed: false
    description: Third-party databases, media articles, public procurement material, analyst reports, and community lists.
    allowed_for:
      - candidate_observations
      - historical_notes
      - gap_filling_candidates
    restrictions:
      - Never auto-resolve without reviewed_by metadata.
```

- [ ] **Step 3: Create accelerator scopes schema**

Create `personal-wiki/domains/ai_infra/data/compute_accelerators/schema/accelerator-scopes.yaml` with:

```yaml
accelerator_scopes:
  gpu:
    name: Graphics Processing Unit
    description: Programmable parallel accelerators commonly used for AI training, inference, graphics, and HPC.
    field_groups:
      - common_specs
      - compute_specs
  npu:
    name: Neural Processing Unit
    description: AI-oriented accelerators marketed as NPUs or neural processors.
    field_groups:
      - common_specs
      - compute_specs
      - role_specific_specs
  tpu:
    name: Tensor Processing Unit
    description: Google TPU accelerators and cloud-visible TPU offerings.
    field_groups:
      - common_specs
      - compute_specs
      - role_specific_specs
  dpu:
    name: Data Processing Unit
    description: Programmable infrastructure processors for networking, storage, security, and virtualization offload.
    field_groups:
      - common_specs
      - role_specific_specs
  ipu:
    name: Infrastructure Processing Unit
    description: Infrastructure offload processors, including Intel IPU-style devices.
    field_groups:
      - common_specs
      - role_specific_specs
  fpga:
    name: Field Programmable Gate Array
    description: Reconfigurable accelerators and FPGA cards used for AI, networking, and custom pipelines.
    field_groups:
      - common_specs
      - role_specific_specs
  dsa:
    name: Domain Specific Accelerator
    description: Domain-specific accelerators that do not fit a narrower accelerator scope.
    field_groups:
      - common_specs
      - compute_specs
      - role_specific_specs
  ai_asic:
    name: AI ASIC
    description: Custom AI accelerators and inference or training ASICs.
    field_groups:
      - common_specs
      - compute_specs
      - role_specific_specs
```

- [ ] **Step 4: Create canonical spec fields**

Create `personal-wiki/domains/ai_infra/data/compute_accelerators/schema/spec-fields.yaml` with:

```yaml
spec_fields:
  memory_capacity:
    group: common_specs
    value_type: number
    canonical_unit: GB
    allowed_units: [GB]
    applies_to: [gpu, npu, tpu, dpu, ipu, fpga, dsa, ai_asic]
    observation_kind: theoretical_or_official
    description: Memory capacity attached to one accelerator or one cloud-visible accelerator slice.
  memory_type:
    group: common_specs
    value_type: string
    canonical_unit: none
    allowed_units: [none]
    applies_to: [gpu, npu, tpu, dpu, ipu, fpga, dsa, ai_asic]
    observation_kind: theoretical_or_official
    description: Memory technology such as HBM2e, HBM3, HBM3e, GDDR6, or DDR.
  memory_bandwidth:
    group: common_specs
    value_type: number
    canonical_unit: TB/s
    allowed_units: [TB/s, GB/s]
    applies_to: [gpu, npu, tpu, dpu, ipu, fpga, dsa, ai_asic]
    observation_kind: theoretical_or_official
    description: Peak memory bandwidth for one accelerator unless the field name says aggregate.
  tdp:
    group: common_specs
    value_type: number
    canonical_unit: W
    allowed_units: [W]
    applies_to: [gpu, npu, tpu, dpu, ipu, fpga, dsa, ai_asic]
    observation_kind: theoretical_or_official
    description: Thermal design power or official maximum board power.
  host_interface:
    group: common_specs
    value_type: string
    canonical_unit: none
    allowed_units: [none]
    applies_to: [gpu, npu, tpu, dpu, ipu, fpga, dsa, ai_asic]
    observation_kind: theoretical_or_official
    description: Host interface such as PCIe Gen5 x16, SXM, OAM, or cloud-integrated.
  form_factor:
    group: common_specs
    value_type: string
    canonical_unit: none
    allowed_units: [none]
    applies_to: [gpu, npu, tpu, dpu, ipu, fpga, dsa, ai_asic]
    observation_kind: theoretical_or_official
    description: Card, module, appliance, or cloud-visible deployment format.
  interconnect:
    group: common_specs
    value_type: string
    canonical_unit: none
    allowed_units: [none]
    applies_to: [gpu, npu, tpu, dpu, ipu, fpga, dsa, ai_asic]
    observation_kind: theoretical_or_official
    description: Accelerator interconnect such as NVLink, Infinity Fabric, TPU ICI, Ethernet, or PCIe.
  fp64_tflops:
    group: compute_specs
    value_type: number
    canonical_unit: TFLOPS
    allowed_units: [TFLOPS]
    applies_to: [gpu, dsa]
    observation_kind: theoretical_peak
    description: Peak FP64 performance.
  fp32_tflops:
    group: compute_specs
    value_type: number
    canonical_unit: TFLOPS
    allowed_units: [TFLOPS]
    applies_to: [gpu, npu, tpu, dsa, ai_asic]
    observation_kind: theoretical_peak
    description: Peak FP32 performance.
  bf16_tflops:
    group: compute_specs
    value_type: number
    canonical_unit: TFLOPS
    allowed_units: [TFLOPS]
    applies_to: [gpu, npu, tpu, dsa, ai_asic]
    observation_kind: theoretical_peak
    description: Peak BF16 tensor or matrix performance.
  fp8_tflops:
    group: compute_specs
    value_type: number
    canonical_unit: TFLOPS
    allowed_units: [TFLOPS]
    applies_to: [gpu, npu, tpu, dsa, ai_asic]
    observation_kind: theoretical_peak
    description: Peak FP8 tensor or matrix performance.
  int8_tops:
    group: compute_specs
    value_type: number
    canonical_unit: TOPS
    allowed_units: [TOPS]
    applies_to: [gpu, npu, tpu, dsa, ai_asic]
    observation_kind: theoretical_peak
    description: Peak INT8 inference performance.
  network_bandwidth:
    group: role_specific_specs
    value_type: number
    canonical_unit: Gb/s
    allowed_units: [Gb/s]
    applies_to: [dpu, ipu]
    observation_kind: theoretical_or_official
    description: Network bandwidth exposed by DPU or IPU ports.
  fpga_lut_count:
    group: role_specific_specs
    value_type: number
    canonical_unit: count
    allowed_units: [count]
    applies_to: [fpga]
    observation_kind: theoretical_or_official
    description: FPGA lookup table count or equivalent logic cells when explicitly mapped.
  fpga_dsp_count:
    group: role_specific_specs
    value_type: number
    canonical_unit: count
    allowed_units: [count]
    applies_to: [fpga]
    observation_kind: theoretical_or_official
    description: FPGA DSP block count.
  cloud_accelerator_count:
    group: role_specific_specs
    value_type: number
    canonical_unit: count
    allowed_units: [count]
    applies_to: [gpu, npu, tpu, dsa, ai_asic]
    observation_kind: cloud_offering
    description: Number of accelerators in a cloud instance, VM size, node, or slice.
  aggregate_memory:
    group: role_specific_specs
    value_type: number
    canonical_unit: GB
    allowed_units: [GB]
    applies_to: [gpu, npu, tpu, dsa, ai_asic]
    observation_kind: cloud_offering
    description: Total accelerator memory in a cloud instance, VM size, node, or slice.
```

- [ ] **Step 5: Create source registry**

Create `personal-wiki/domains/ai_infra/data/compute_accelerators/sources/source-registry.yaml` with:

```yaml
sources:
  - source_id: nvidia-h200-product-page
    name: NVIDIA H200 Tensor Core GPU product page
    url: https://www.nvidia.com/en-us/data-center/h200/
    source_rank: S1
    publisher: NVIDIA
    source_type: product_page
    trust_policy: official_vendor_single_accelerator
    crawl_policy: snapshot_and_candidate_extract
    notes: Official NVIDIA page for H200 memory and product positioning.
  - source_id: amd-mi325x-product-page
    name: AMD Instinct MI325X product page
    url: https://www.amd.com/en/products/accelerators/instinct/mi300/mi325x.html
    source_rank: S1
    publisher: AMD
    source_type: product_page
    trust_policy: official_vendor_single_accelerator
    crawl_policy: snapshot_and_candidate_extract
    notes: Official AMD page for MI325X accelerator specifications.
  - source_id: intel-gaudi-3-white-paper
    name: Intel Gaudi 3 AI accelerator white paper
    url: https://cdrdv2-public.intel.com/817486/gaudi-3-ai-accelerator-white-paper.pdf
    source_rank: S1
    publisher: Intel
    source_type: white_paper
    trust_policy: official_vendor_single_accelerator
    crawl_policy: snapshot_and_candidate_extract
    notes: Official Intel white paper for Gaudi 3 accelerator specifications.
  - source_id: nvidia-bluefield-3-product-page
    name: NVIDIA BlueField-3 DPU product page
    url: https://www.nvidia.com/en-us/networking/products/data-processing-unit/
    source_rank: S1
    publisher: NVIDIA
    source_type: product_page
    trust_policy: official_vendor_dpu
    crawl_policy: snapshot_and_candidate_extract
    notes: Official NVIDIA DPU page for BlueField-3 networking and offload positioning.
  - source_id: amd-alveo-v80-product-page
    name: AMD Alveo V80 compute accelerator product page
    url: https://www.amd.com/en/products/accelerators/alveo/v80.html
    source_rank: S1
    publisher: AMD
    source_type: product_page
    trust_policy: official_vendor_fpga_card
    crawl_policy: snapshot_and_candidate_extract
    notes: Official AMD page for Alveo V80 FPGA-based compute accelerator specifications.
  - source_id: microsoft-maia-200-announcement
    name: Microsoft Maia 200 official announcement
    url: https://blogs.microsoft.com/blog/2026/01/26/maia-200-the-ai-accelerator-built-for-inference/
    source_rank: S1
    publisher: Microsoft
    source_type: official_blog
    trust_policy: official_vendor_ai_accelerator
    crawl_policy: snapshot_and_candidate_extract
    notes: Official Microsoft announcement for Maia 200 inference accelerator specifications.
  - source_id: aws-trn2-instance-page
    name: AWS EC2 Trn2 instances page
    url: https://aws.amazon.com/ec2/instance-types/trn2/
    source_rank: S2
    publisher: AWS
    source_type: cloud_doc
    trust_policy: official_cloud_offering
    crawl_policy: snapshot_and_candidate_extract
    notes: Official AWS page for Trainium2 cloud offerings.
  - source_id: google-cloud-tpu-docs
    name: Google Cloud TPU documentation
    url: https://cloud.google.com/tpu/docs
    source_rank: S2
    publisher: Google Cloud
    source_type: cloud_doc
    trust_policy: official_cloud_offering
    crawl_policy: snapshot_and_candidate_extract
    notes: Official Google Cloud TPU documentation entry point.
  - source_id: mlcommons-training-results
    name: MLCommons training results
    url: https://mlcommons.org/benchmarks/training/
    source_rank: S3
    publisher: MLCommons
    source_type: benchmark_index
    trust_policy: benchmark_submission
    crawl_policy: snapshot_only
    notes: Benchmark source for submitted system results, not theoretical peak specs.
  - source_id: runtime-nvidia-smi
    name: NVIDIA nvidia-smi runtime probe
    url: https://docs.nvidia.com/deploy/nvidia-smi/index.html
    source_rank: S4
    publisher: NVIDIA
    source_type: runtime_probe
    trust_policy: observed_runtime_state
    crawl_policy: manual_probe_only
    notes: Runtime inventory and telemetry source for deployed NVIDIA accelerators.
  - source_id: techpowerup-gpu-database
    name: TechPowerUp GPU database
    url: https://www.techpowerup.com/gpu-specs/
    source_rank: S5
    publisher: TechPowerUp
    source_type: third_party_database
    trust_policy: review_required
    crawl_policy: snapshot_only_no_auto_resolve
    notes: Third-party database; observations require review before resolution.
```

- [ ] **Step 6: Verify YAML parses**

Run:

```bash
python - <<'PY'
from pathlib import Path
import yaml
base = Path("personal-wiki/domains/ai_infra/data/compute_accelerators")
for path in [
    base / "schema/source-ranks.yaml",
    base / "schema/accelerator-scopes.yaml",
    base / "schema/spec-fields.yaml",
    base / "sources/source-registry.yaml",
]:
    with path.open(encoding="utf-8") as handle:
        yaml.safe_load(handle)
    print(path)
PY
```

Expected: four file paths printed and exit code 0.

- [ ] **Step 7: Commit Task 1**

Run:

```bash
git add \
  personal-wiki/domains/ai_infra/data/compute_accelerators/README.md \
  personal-wiki/domains/ai_infra/data/compute_accelerators/schema/source-ranks.yaml \
  personal-wiki/domains/ai_infra/data/compute_accelerators/schema/accelerator-scopes.yaml \
  personal-wiki/domains/ai_infra/data/compute_accelerators/schema/spec-fields.yaml \
  personal-wiki/domains/ai_infra/data/compute_accelerators/sources/source-registry.yaml
git commit -m "feat(wiki): seed accelerator catalog schema"
```

Expected: commit succeeds and includes only Task 1 files.

## Task 2: Add Sample SKUs, Observations, Resolved Specs, and Candidates Contract

**Files:**
- Create: `personal-wiki/domains/ai_infra/data/compute_accelerators/skus/sample-skus.yaml`
- Create: `personal-wiki/domains/ai_infra/data/compute_accelerators/observations/sample-observations.yaml`
- Create: `personal-wiki/domains/ai_infra/data/compute_accelerators/resolved/sample-resolved-specs.yaml`
- Create: `personal-wiki/domains/ai_infra/data/compute_accelerators/candidates/README.md`

- [ ] **Step 1: Create sample SKU records**

Create `personal-wiki/domains/ai_infra/data/compute_accelerators/skus/sample-skus.yaml` with:

```yaml
skus:
  - sku_id: nvidia-h200-sxm
    vendor_id: nvidia
    family_id: nvidia-hopper
    canonical_name: NVIDIA H200 SXM
    aliases: [H200 SXM, H200 Tensor Core GPU]
    scope: gpu
    form_factor: SXM module
    release_status: released
    source_refs: [nvidia-h200-product-page]
  - sku_id: amd-mi325x-oam
    vendor_id: amd
    family_id: amd-instinct-mi300
    canonical_name: AMD Instinct MI325X
    aliases: [MI325X, Instinct MI325X]
    scope: gpu
    form_factor: OAM module
    release_status: released
    source_refs: [amd-mi325x-product-page]
  - sku_id: intel-gaudi-3-hl-338
    vendor_id: intel
    family_id: intel-gaudi-3
    canonical_name: Intel Gaudi 3 HL-338
    aliases: [Gaudi 3, HL-338]
    scope: ai_asic
    form_factor: OAM module
    release_status: released
    source_refs: [intel-gaudi-3-white-paper]
  - sku_id: nvidia-bluefield-3-dpu
    vendor_id: nvidia
    family_id: nvidia-bluefield
    canonical_name: NVIDIA BlueField-3 DPU
    aliases: [BlueField-3, BF3]
    scope: dpu
    form_factor: PCIe card or integrated DPU
    release_status: released
    source_refs: [nvidia-bluefield-3-product-page]
  - sku_id: aws-trainium2-trn2-offering
    vendor_id: aws
    family_id: aws-trainium
    canonical_name: AWS Trainium2 Trn2 offering
    aliases: [Trainium2, Trn2]
    scope: ai_asic
    form_factor: cloud offering
    release_status: released
    source_refs: [aws-trn2-instance-page]
  - sku_id: google-cloud-tpu-v5p-offering
    vendor_id: google
    family_id: google-cloud-tpu
    canonical_name: Google Cloud TPU v5p offering
    aliases: [Cloud TPU v5p, TPU v5p]
    scope: tpu
    form_factor: cloud offering
    release_status: released
    source_refs: [google-cloud-tpu-docs]
  - sku_id: xilinx-alveo-v80
    vendor_id: amd
    family_id: amd-xilinx-alveo
    canonical_name: AMD Alveo V80
    aliases: [Xilinx Alveo V80, Alveo V80]
    scope: fpga
    form_factor: PCIe card
    release_status: released
    source_refs: [amd-alveo-v80-product-page]
  - sku_id: microsoft-maia-200
    vendor_id: microsoft
    family_id: microsoft-maia
    canonical_name: Microsoft Maia 200
    aliases: [Azure Maia 200, Maia 200]
    scope: dsa
    form_factor: cloud-integrated accelerator
    release_status: announced
    source_refs: [microsoft-maia-200-announcement]
```

- [ ] **Step 2: Create sample observations**

Create `personal-wiki/domains/ai_infra/data/compute_accelerators/observations/sample-observations.yaml` with:

```yaml
observations:
  - observation_id: obs-nvidia-h200-memory-capacity
    sku_id: nvidia-h200-sxm
    field: memory_capacity
    value: 141
    unit: GB
    source_id: nvidia-h200-product-page
    source_rank: S1
    captured_at: "2026-06-27"
    source_locator: "NVIDIA H200 product page; memory specifications section"
    is_official: true
    is_inferred: false
    confidence: high
    notes: Official page lists 141GB HBM3e for H200.
  - observation_id: obs-nvidia-h200-memory-bandwidth
    sku_id: nvidia-h200-sxm
    field: memory_bandwidth
    value: 4.8
    unit: TB/s
    source_id: nvidia-h200-product-page
    source_rank: S1
    captured_at: "2026-06-27"
    source_locator: "NVIDIA H200 product page; memory specifications section"
    is_official: true
    is_inferred: false
    confidence: high
    notes: Official page lists up to 4.8TB/s memory bandwidth.
  - observation_id: obs-amd-mi325x-memory-capacity
    sku_id: amd-mi325x-oam
    field: memory_capacity
    value: 256
    unit: GB
    source_id: amd-mi325x-product-page
    source_rank: S1
    captured_at: "2026-06-27"
    source_locator: "AMD MI325X product page; product specifications"
    is_official: true
    is_inferred: false
    confidence: high
    notes: Official AMD page lists 256GB HBM3E memory.
  - observation_id: obs-intel-gaudi-3-memory-capacity
    sku_id: intel-gaudi-3-hl-338
    field: memory_capacity
    value: 128
    unit: GB
    source_id: intel-gaudi-3-white-paper
    source_rank: S1
    captured_at: "2026-06-27"
    source_locator: "Intel Gaudi 3 white paper; accelerator memory"
    is_official: true
    is_inferred: false
    confidence: high
    notes: Official Intel white paper lists 128GB HBM2e.
  - observation_id: obs-bluefield-3-network-bandwidth
    sku_id: nvidia-bluefield-3-dpu
    field: network_bandwidth
    value: 400
    unit: Gb/s
    source_id: nvidia-bluefield-3-product-page
    source_rank: S1
    captured_at: "2026-06-27"
    source_locator: "NVIDIA BlueField-3 product page; Ethernet and InfiniBand connectivity"
    is_official: true
    is_inferred: false
    confidence: medium
    notes: Represents a high-level official product capability; exact card SKUs can vary.
  - observation_id: obs-aws-trn2-accelerator-count
    sku_id: aws-trainium2-trn2-offering
    field: cloud_accelerator_count
    value: 16
    unit: count
    source_id: aws-trn2-instance-page
    source_rank: S2
    captured_at: "2026-06-27"
    source_locator: "AWS Trn2 page; Trn2 instance family overview"
    is_official: true
    is_inferred: false
    confidence: medium
    notes: Cloud offering aggregate field; does not describe one chip package.
  - observation_id: obs-google-tpu-v5p-source-entry
    sku_id: google-cloud-tpu-v5p-offering
    field: form_factor
    value: cloud offering
    unit: none
    source_id: google-cloud-tpu-docs
    source_rank: S2
    captured_at: "2026-06-27"
    source_locator: "Google Cloud TPU documentation entry point"
    is_official: true
    is_inferred: false
    confidence: medium
    notes: Source entry validates TPU scope coverage; detailed per-version fields can be added later.
  - observation_id: obs-microsoft-maia-200-memory-capacity
    sku_id: microsoft-maia-200
    field: memory_capacity
    value: 216
    unit: GB
    source_id: microsoft-maia-200-announcement
    source_rank: S1
    captured_at: "2026-06-27"
    source_locator: "Microsoft Maia 200 announcement; memory system description"
    is_official: true
    is_inferred: false
    confidence: high
    notes: Official Microsoft announcement lists 216GB HBM3e.
  - observation_id: obs-microsoft-maia-200-memory-bandwidth
    sku_id: microsoft-maia-200
    field: memory_bandwidth
    value: 7
    unit: TB/s
    source_id: microsoft-maia-200-announcement
    source_rank: S1
    captured_at: "2026-06-27"
    source_locator: "Microsoft Maia 200 announcement; memory system description"
    is_official: true
    is_inferred: false
    confidence: high
    notes: Official Microsoft announcement lists 7TB/s HBM3e bandwidth.
```

- [ ] **Step 3: Create sample resolved specs**

Create `personal-wiki/domains/ai_infra/data/compute_accelerators/resolved/sample-resolved-specs.yaml` with:

```yaml
resolved_specs:
  - sku_id: nvidia-h200-sxm
    resolved_fields:
      memory_capacity:
        value: 141
        unit: GB
        source_observation_id: obs-nvidia-h200-memory-capacity
        resolved_by: rule
        confidence: high
        conflict_status: clean
        updated_at: "2026-06-27"
      memory_bandwidth:
        value: 4.8
        unit: TB/s
        source_observation_id: obs-nvidia-h200-memory-bandwidth
        resolved_by: rule
        confidence: high
        conflict_status: clean
        updated_at: "2026-06-27"
  - sku_id: amd-mi325x-oam
    resolved_fields:
      memory_capacity:
        value: 256
        unit: GB
        source_observation_id: obs-amd-mi325x-memory-capacity
        resolved_by: rule
        confidence: high
        conflict_status: clean
        updated_at: "2026-06-27"
  - sku_id: intel-gaudi-3-hl-338
    resolved_fields:
      memory_capacity:
        value: 128
        unit: GB
        source_observation_id: obs-intel-gaudi-3-memory-capacity
        resolved_by: rule
        confidence: high
        conflict_status: clean
        updated_at: "2026-06-27"
  - sku_id: nvidia-bluefield-3-dpu
    resolved_fields:
      network_bandwidth:
        value: 400
        unit: Gb/s
        source_observation_id: obs-bluefield-3-network-bandwidth
        resolved_by: rule
        confidence: medium
        conflict_status: clean
        updated_at: "2026-06-27"
  - sku_id: aws-trainium2-trn2-offering
    resolved_fields:
      cloud_accelerator_count:
        value: 16
        unit: count
        source_observation_id: obs-aws-trn2-accelerator-count
        resolved_by: rule
        confidence: medium
        conflict_status: clean
        updated_at: "2026-06-27"
  - sku_id: microsoft-maia-200
    resolved_fields:
      memory_capacity:
        value: 216
        unit: GB
        source_observation_id: obs-microsoft-maia-200-memory-capacity
        resolved_by: rule
        confidence: high
        conflict_status: clean
        updated_at: "2026-06-27"
      memory_bandwidth:
        value: 7
        unit: TB/s
        source_observation_id: obs-microsoft-maia-200-memory-bandwidth
        resolved_by: rule
        confidence: high
        conflict_status: clean
        updated_at: "2026-06-27"
```

- [ ] **Step 4: Create candidate extraction contract**

Create `personal-wiki/domains/ai_infra/data/compute_accelerators/candidates/README.md` with:

```markdown
# Accelerator Spec Candidates

Crawler and extractor output should land here before it becomes an observation
or resolved specification.

Candidate files use YAML and contain proposed records only. They do not change
accepted values until reviewed by a resolver or human reviewer.

## Candidate Shape

```yaml
candidates:
  - candidate_id: candidate-source-sku-field
    source_id: nvidia-h200-product-page
    sku_hint: NVIDIA H200 SXM
    field: memory_capacity
    raw_value: "141GB"
    normalized_value: 141
    normalized_unit: GB
    source_rank: S1
    confidence: high
    review_status: pending
    notes: Extracted from official product page.
```

## Review Rules

- S1 candidates can become observations when field extraction is unambiguous.
- S2 candidates update cloud offering fields, not single-card specs.
- S3 benchmark candidates stay benchmark-specific.
- S4 candidates stay observed/runtime-specific.
- S5 candidates require human review before resolution.
```

- [ ] **Step 5: Verify YAML parses**

Run:

```bash
python - <<'PY'
from pathlib import Path
import yaml
base = Path("personal-wiki/domains/ai_infra/data/compute_accelerators")
for path in [
    base / "skus/sample-skus.yaml",
    base / "observations/sample-observations.yaml",
    base / "resolved/sample-resolved-specs.yaml",
]:
    with path.open(encoding="utf-8") as handle:
        yaml.safe_load(handle)
    print(path)
PY
```

Expected: three file paths printed and exit code 0.

- [ ] **Step 6: Commit Task 2**

Run:

```bash
git add \
  personal-wiki/domains/ai_infra/data/compute_accelerators/skus/sample-skus.yaml \
  personal-wiki/domains/ai_infra/data/compute_accelerators/observations/sample-observations.yaml \
  personal-wiki/domains/ai_infra/data/compute_accelerators/resolved/sample-resolved-specs.yaml \
  personal-wiki/domains/ai_infra/data/compute_accelerators/candidates/README.md
git commit -m "feat(wiki): add accelerator sample specs"
```

Expected: commit succeeds and includes only Task 2 files.

## Task 3: Add Structured Catalog Validator and CLI Command

**Files:**
- Create: `personal-wiki/tools/wiki_cli/accelerator_catalog.py`
- Modify: `personal-wiki/tools/wiki_cli/cli.py`
- Create: `personal-wiki/tests/test_accelerator_catalog.py`

- [ ] **Step 1: Write validator tests**

Create `personal-wiki/tests/test_accelerator_catalog.py` with:

```python
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from personal_wiki_test_loader import load_cli_module


accelerator_catalog = load_cli_module("accelerator_catalog")


def write_yaml(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def build_catalog(root: Path) -> Path:
    base = root / "domains/ai_infra/data/compute_accelerators"
    write_yaml(
        base / "schema/source-ranks.yaml",
        {
            "source_ranks": {
                "S1": {"auto_resolve_allowed": "conditional"},
                "S5": {"auto_resolve_allowed": False},
            }
        },
    )
    write_yaml(
        base / "schema/accelerator-scopes.yaml",
        {"accelerator_scopes": {"gpu": {}, "dpu": {}}},
    )
    write_yaml(
        base / "schema/spec-fields.yaml",
        {
            "spec_fields": {
                "memory_capacity": {
                    "canonical_unit": "GB",
                    "allowed_units": ["GB"],
                    "applies_to": ["gpu"],
                },
                "network_bandwidth": {
                    "canonical_unit": "Gb/s",
                    "allowed_units": ["Gb/s"],
                    "applies_to": ["dpu"],
                },
            }
        },
    )
    write_yaml(
        base / "sources/source-registry.yaml",
        {
            "sources": [
                {"source_id": "official-source", "source_rank": "S1"},
                {"source_id": "third-party-source", "source_rank": "S5"},
            ]
        },
    )
    write_yaml(
        base / "skus/sample-skus.yaml",
        {
            "skus": [
                {
                    "sku_id": "gpu-sku",
                    "vendor_id": "vendor",
                    "canonical_name": "GPU SKU",
                    "scope": "gpu",
                    "source_refs": ["official-source"],
                }
            ]
        },
    )
    write_yaml(
        base / "observations/sample-observations.yaml",
        {
            "observations": [
                {
                    "observation_id": "obs-memory",
                    "sku_id": "gpu-sku",
                    "field": "memory_capacity",
                    "value": 141,
                    "unit": "GB",
                    "source_id": "official-source",
                    "source_rank": "S1",
                    "captured_at": "2026-06-27",
                    "source_locator": "fixture",
                    "is_official": True,
                    "is_inferred": False,
                    "confidence": "high",
                }
            ]
        },
    )
    write_yaml(
        base / "resolved/sample-resolved-specs.yaml",
        {
            "resolved_specs": [
                {
                    "sku_id": "gpu-sku",
                    "resolved_fields": {
                        "memory_capacity": {
                            "value": 141,
                            "unit": "GB",
                            "source_observation_id": "obs-memory",
                            "resolved_by": "rule",
                            "confidence": "high",
                            "conflict_status": "clean",
                            "updated_at": "2026-06-27",
                        }
                    },
                }
            ]
        },
    )
    return base


def test_validate_catalog_accepts_consistent_fixture(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    build_catalog(root)

    issues = accelerator_catalog.validate_catalog(root)

    assert issues == []


def test_validate_catalog_rejects_unknown_scope(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    base = build_catalog(root)
    sku_path = base / "skus/sample-skus.yaml"
    payload = yaml.safe_load(sku_path.read_text(encoding="utf-8"))
    payload["skus"][0]["scope"] = "quantum"
    write_yaml(sku_path, payload)

    issues = accelerator_catalog.validate_catalog(root)

    assert any(issue.code == "unknown_scope" for issue in issues)


def test_validate_catalog_rejects_resolved_field_without_observation(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    base = build_catalog(root)
    resolved_path = base / "resolved/sample-resolved-specs.yaml"
    payload = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    payload["resolved_specs"][0]["resolved_fields"]["memory_capacity"][
        "source_observation_id"
    ] = "missing-observation"
    write_yaml(resolved_path, payload)

    issues = accelerator_catalog.validate_catalog(root)

    assert any(issue.code == "missing_observation" for issue in issues)


def test_validate_catalog_rejects_s5_auto_resolve_without_review(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    base = build_catalog(root)
    observations_path = base / "observations/sample-observations.yaml"
    payload = yaml.safe_load(observations_path.read_text(encoding="utf-8"))
    payload["observations"][0]["source_id"] = "third-party-source"
    payload["observations"][0]["source_rank"] = "S5"
    payload["observations"][0].pop("reviewed_by", None)
    write_yaml(observations_path, payload)

    issues = accelerator_catalog.validate_catalog(root)

    assert any(issue.code == "s5_resolved_without_review" for issue in issues)


def test_validate_catalog_rejects_field_not_applicable_to_scope(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    base = build_catalog(root)
    observations_path = base / "observations/sample-observations.yaml"
    payload = yaml.safe_load(observations_path.read_text(encoding="utf-8"))
    payload["observations"][0]["field"] = "network_bandwidth"
    payload["observations"][0]["unit"] = "Gb/s"
    write_yaml(observations_path, payload)
    resolved_path = base / "resolved/sample-resolved-specs.yaml"
    resolved = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    field_payload = resolved["resolved_specs"][0]["resolved_fields"].pop("memory_capacity")
    field_payload["unit"] = "Gb/s"
    resolved["resolved_specs"][0]["resolved_fields"]["network_bandwidth"] = field_payload
    write_yaml(resolved_path, resolved)

    issues = accelerator_catalog.validate_catalog(root)

    assert any(issue.code == "field_not_applicable" for issue in issues)


def test_validate_accelerators_cli_reports_success_for_repo_catalog():
    cli = Path(__file__).resolve().parents[1] / "tools/wiki_cli/cli.py"

    result = subprocess.run(
        [
            sys.executable,
            str(cli),
            "--root",
            str(Path(__file__).resolve().parents[1]),
            "validate-accelerators",
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert "No accelerator catalog validation issues" in result.stdout
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=personal-wiki/tests pytest -q personal-wiki/tests/test_accelerator_catalog.py
```

Expected: FAIL during import or CLI command because `accelerator_catalog.py` and `validate-accelerators` do not exist.

- [ ] **Step 3: Implement accelerator catalog validator**

Create `personal-wiki/tools/wiki_cli/accelerator_catalog.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


CATALOG_RELATIVE = Path("domains/ai_infra/data/compute_accelerators")


@dataclass(frozen=True)
class CatalogIssue:
    code: str
    path: Path
    message: str


def validate_catalog(root: Path) -> list[CatalogIssue]:
    root = Path(root)
    base = root / CATALOG_RELATIVE
    issues: list[CatalogIssue] = []

    source_ranks_path = base / "schema/source-ranks.yaml"
    scopes_path = base / "schema/accelerator-scopes.yaml"
    fields_path = base / "schema/spec-fields.yaml"
    sources_path = base / "sources/source-registry.yaml"
    skus_path = base / "skus/sample-skus.yaml"
    observations_path = base / "observations/sample-observations.yaml"
    resolved_path = base / "resolved/sample-resolved-specs.yaml"

    source_ranks = _load_mapping(source_ranks_path, "source_ranks", issues)
    scopes = _load_mapping(scopes_path, "accelerator_scopes", issues)
    fields = _load_mapping(fields_path, "spec_fields", issues)
    sources_payload = _load_list(sources_path, "sources", issues)
    skus_payload = _load_list(skus_path, "skus", issues)
    observations_payload = _load_list(observations_path, "observations", issues)
    resolved_payload = _load_list(resolved_path, "resolved_specs", issues)

    if issues:
        return issues

    source_ids = _index_by_id(sources_payload, "source_id", sources_path, issues)
    sku_ids = _index_by_id(skus_payload, "sku_id", skus_path, issues)
    observation_ids = _index_by_id(
        observations_payload, "observation_id", observations_path, issues
    )

    for source in sources_payload:
        rank = source.get("source_rank")
        if rank not in source_ranks:
            issues.append(
                CatalogIssue(
                    "unknown_source_rank",
                    sources_path,
                    f"source {source.get('source_id')} uses unknown source_rank {rank}",
                )
            )

    for sku in skus_payload:
        sku_id = sku.get("sku_id")
        for key in ("vendor_id", "scope", "canonical_name", "source_refs"):
            if not _has_value(sku.get(key)):
                issues.append(
                    CatalogIssue(
                        "missing_sku_field",
                        skus_path,
                        f"sku {sku_id or '<unknown>'} missing required field {key}",
                    )
                )
        scope = sku.get("scope")
        if scope not in scopes:
            issues.append(
                CatalogIssue(
                    "unknown_scope",
                    skus_path,
                    f"sku {sku_id or '<unknown>'} uses unknown scope {scope}",
                )
            )
        for source_ref in _list_value(sku.get("source_refs")):
            if source_ref not in source_ids:
                issues.append(
                    CatalogIssue(
                        "missing_source_ref",
                        skus_path,
                        f"sku {sku_id or '<unknown>'} references unknown source {source_ref}",
                    )
                )

    for observation in observations_payload:
        observation_id = observation.get("observation_id")
        sku_id = observation.get("sku_id")
        field = observation.get("field")
        unit = observation.get("unit")
        source_id = observation.get("source_id")
        source_rank = observation.get("source_rank")
        for key in (
            "observation_id",
            "sku_id",
            "field",
            "value",
            "unit",
            "source_rank",
            "captured_at",
            "source_locator",
            "is_official",
            "is_inferred",
            "confidence",
        ):
            if not _has_value(observation.get(key)):
                issues.append(
                    CatalogIssue(
                        "missing_observation_field",
                        observations_path,
                        f"observation {observation_id or '<unknown>'} missing required field {key}",
                    )
                )
        if sku_id not in sku_ids:
            issues.append(
                CatalogIssue(
                    "unknown_observation_sku",
                    observations_path,
                    f"observation {observation_id or '<unknown>'} references unknown sku {sku_id}",
                )
            )
        if field not in fields:
            issues.append(
                CatalogIssue(
                    "unknown_field",
                    observations_path,
                    f"observation {observation_id or '<unknown>'} uses unknown field {field}",
                )
            )
        elif unit not in _list_value(fields[field].get("allowed_units")):
            issues.append(
                CatalogIssue(
                    "invalid_unit",
                    observations_path,
                    f"observation {observation_id or '<unknown>'} field {field} uses invalid unit {unit}",
                )
            )
        if source_id:
            if source_id not in source_ids:
                issues.append(
                    CatalogIssue(
                        "unknown_observation_source",
                        observations_path,
                        f"observation {observation_id or '<unknown>'} references unknown source {source_id}",
                    )
                )
            elif source_rank != source_ids[source_id].get("source_rank"):
                issues.append(
                    CatalogIssue(
                        "source_rank_mismatch",
                        observations_path,
                        f"observation {observation_id or '<unknown>'} source_rank {source_rank} does not match source {source_id}",
                    )
                )
        elif not observation.get("raw_path"):
            issues.append(
                CatalogIssue(
                    "missing_observation_source",
                    observations_path,
                    f"observation {observation_id or '<unknown>'} needs source_id or raw_path",
                )
            )
        if sku_id in sku_ids and field in fields:
            scope = sku_ids[sku_id].get("scope")
            if scope not in _list_value(fields[field].get("applies_to")):
                issues.append(
                    CatalogIssue(
                        "field_not_applicable",
                        observations_path,
                        f"field {field} does not apply to sku {sku_id} scope {scope}",
                    )
                )

    resolved_observation_ids: set[str] = set()
    for resolved in resolved_payload:
        sku_id = resolved.get("sku_id")
        if sku_id not in sku_ids:
            issues.append(
                CatalogIssue(
                    "unknown_resolved_sku",
                    resolved_path,
                    f"resolved spec references unknown sku {sku_id}",
                )
            )
        resolved_fields = resolved.get("resolved_fields")
        if not isinstance(resolved_fields, dict) or not resolved_fields:
            issues.append(
                CatalogIssue(
                    "missing_resolved_fields",
                    resolved_path,
                    f"resolved spec {sku_id or '<unknown>'} has no resolved_fields mapping",
                )
            )
            continue
        for field, value in resolved_fields.items():
            if field not in fields:
                issues.append(
                    CatalogIssue(
                        "unknown_resolved_field",
                        resolved_path,
                        f"resolved spec {sku_id or '<unknown>'} uses unknown field {field}",
                    )
                )
                continue
            if sku_id in sku_ids:
                scope = sku_ids[sku_id].get("scope")
                if scope not in _list_value(fields[field].get("applies_to")):
                    issues.append(
                        CatalogIssue(
                            "field_not_applicable",
                            resolved_path,
                            f"resolved field {field} does not apply to sku {sku_id} scope {scope}",
                        )
                    )
            unit = value.get("unit") if isinstance(value, dict) else None
            if unit not in _list_value(fields[field].get("allowed_units")):
                issues.append(
                    CatalogIssue(
                        "invalid_resolved_unit",
                        resolved_path,
                        f"resolved spec {sku_id or '<unknown>'} field {field} uses invalid unit {unit}",
                    )
                )
            observation_id = value.get("source_observation_id") if isinstance(value, dict) else None
            if observation_id not in observation_ids:
                issues.append(
                    CatalogIssue(
                        "missing_observation",
                        resolved_path,
                        f"resolved spec {sku_id or '<unknown>'} field {field} references missing observation {observation_id}",
                    )
                )
                continue
            resolved_observation_ids.add(str(observation_id))
            observation = observation_ids[observation_id]
            if observation.get("sku_id") != sku_id or observation.get("field") != field:
                issues.append(
                    CatalogIssue(
                        "observation_field_mismatch",
                        resolved_path,
                        f"resolved spec {sku_id or '<unknown>'} field {field} points to incompatible observation {observation_id}",
                    )
                )
            if observation.get("source_rank") == "S5" and not observation.get("reviewed_by"):
                issues.append(
                    CatalogIssue(
                        "s5_resolved_without_review",
                        resolved_path,
                        f"resolved spec {sku_id or '<unknown>'} field {field} uses S5 observation {observation_id} without reviewed_by",
                    )
                )

    return issues


def _load_yaml(path: Path, issues: list[CatalogIssue]) -> Any:
    if not path.exists():
        issues.append(CatalogIssue("missing_file", path, f"missing catalog file {path}"))
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as error:
        issues.append(CatalogIssue("invalid_yaml", path, f"invalid YAML: {error}"))
        return {}


def _load_mapping(path: Path, key: str, issues: list[CatalogIssue]) -> dict[str, Any]:
    payload = _load_yaml(path, issues)
    value = payload.get(key) if isinstance(payload, dict) else None
    if not isinstance(value, dict):
        issues.append(CatalogIssue("invalid_catalog_shape", path, f"{key} must be a mapping"))
        return {}
    return value


def _load_list(path: Path, key: str, issues: list[CatalogIssue]) -> list[dict[str, Any]]:
    payload = _load_yaml(path, issues)
    value = payload.get(key) if isinstance(payload, dict) else None
    if not isinstance(value, list):
        issues.append(CatalogIssue("invalid_catalog_shape", path, f"{key} must be a list"))
        return []
    objects: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            issues.append(
                CatalogIssue(
                    "invalid_catalog_shape",
                    path,
                    f"{key}[{index}] must be a mapping",
                )
            )
        else:
            objects.append(item)
    return objects


def _index_by_id(
    rows: list[dict[str, Any]],
    key: str,
    path: Path,
    issues: list[CatalogIssue],
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not _has_value(value):
            issues.append(
                CatalogIssue("missing_id", path, f"row missing required identifier {key}")
            )
            continue
        text = str(value)
        if text in indexed:
            issues.append(CatalogIssue("duplicate_id", path, f"duplicate {key}: {text}"))
            continue
        indexed[text] = row
    return indexed


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_has_value(item) for item in value)
    return True


def _list_value(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
```

- [ ] **Step 4: Add CLI command**

Modify `personal-wiki/tools/wiki_cli/cli.py`.

Add imports next to the existing local imports:

```python
    import accelerator_catalog  # type: ignore
```

and in the package import branch:

```python
    from . import accelerator_catalog
```

Add the subparser after the existing validate parser:

```python
    subparsers.add_parser("validate-accelerators")
```

Add command dispatch after the existing validate dispatch:

```python
        if args.command == "validate-accelerators":
            return _run_validate_accelerators(root)
```

Add this function after `_run_validate`:

```python
def _run_validate_accelerators(root: Path) -> int:
    issues = accelerator_catalog.validate_catalog(root)
    if issues:
        for issue in issues:
            print(f"{issue.code} {issue.path} {issue.message}")
        return 1
    print("No accelerator catalog validation issues")
    return 0
```

- [ ] **Step 5: Run validator tests**

Run:

```bash
PYTHONPATH=personal-wiki/tests pytest -q personal-wiki/tests/test_accelerator_catalog.py
```

Expected: PASS.

- [ ] **Step 6: Run the validator against the real catalog**

Run:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators
```

Expected:

```text
No accelerator catalog validation issues
```

- [ ] **Step 7: Commit Task 3**

Run:

```bash
git add \
  personal-wiki/tools/wiki_cli/accelerator_catalog.py \
  personal-wiki/tools/wiki_cli/cli.py \
  personal-wiki/tests/test_accelerator_catalog.py
git commit -m "feat(wiki): validate accelerator catalog data"
```

Expected: commit succeeds and includes only Task 3 files.

## Task 4: Add Curated Wiki Pages and Rebuild Domain Index

**Files:**
- Create: `personal-wiki/domains/ai_infra/wiki/references/compute-accelerator-spec-sources.md`
- Create: `personal-wiki/domains/ai_infra/wiki/references/compute-accelerator-field-glossary.md`
- Create: `personal-wiki/domains/ai_infra/wiki/projects/compute-accelerator-spec-catalog.md`
- Create: `personal-wiki/domains/ai_infra/wiki/projects/compute-accelerator-crawler.md`
- Modify: `personal-wiki/domains/ai_infra/wiki/index.md`

- [ ] **Step 1: Create source policy reference page**

Create `personal-wiki/domains/ai_infra/wiki/references/compute-accelerator-spec-sources.md` with:

```markdown
---
type: Reference
title: Compute Accelerator Spec Sources
description: Source ranking and provenance policy for the compute accelerator specification catalog.
domain: ai_infra
status: reviewed
aliases:
  - accelerator spec sources
  - compute accelerator source ranks
tags:
  - accelerators
  - provenance
  - specs
source_refs:
  - ../../data/compute_accelerators/schema/source-ranks.yaml
  - ../../data/compute_accelerators/sources/source-registry.yaml
---

# Summary

Compute accelerator specifications are resolved from field-level observations,
not copied directly from one flat table. Source rank controls whether a value
can become a resolved field automatically or must stay pending review.

# Source Ranks

- S1: official vendor specifications for card, module, chip, software, and
  support information.
- S2: official cloud provider documentation for instance, VM, node, and
  cloud-visible accelerator offerings.
- S3: standards, registries, and benchmark submissions.
- S4: runtime and inventory probe output.
- S5: third-party, media, procurement, analyst, and community sources that
  require review before resolution.

# Resolution Policy

S1 sources can resolve core single-accelerator fields when extraction is
unambiguous. S2 sources resolve cloud offering fields and do not overwrite
single-card vendor specs. S3 benchmark data stays benchmark-specific. S4 probe
data stays observed/runtime-specific. S5 data remains candidate-only unless a
reviewer is recorded.

# Citations

- ../../data/compute_accelerators/schema/source-ranks.yaml
- ../../data/compute_accelerators/sources/source-registry.yaml
```

- [ ] **Step 2: Create field glossary reference page**

Create `personal-wiki/domains/ai_infra/wiki/references/compute-accelerator-field-glossary.md` with:

```markdown
---
type: Reference
title: Compute Accelerator Field Glossary
description: Canonical field names, units, and scope applicability for accelerator specifications.
domain: ai_infra
status: reviewed
aliases:
  - accelerator field glossary
  - accelerator spec fields
tags:
  - accelerators
  - schema
  - specs
source_refs:
  - ../../data/compute_accelerators/schema/accelerator-scopes.yaml
  - ../../data/compute_accelerators/schema/spec-fields.yaml
---

# Summary

The catalog separates common fields, compute fields, and role-specific fields
so GPU, NPU, TPU, DPU, IPU, FPGA, DSA, and AI ASIC records can share one data
model without forcing every accelerator into GPU-style metrics.

# Field Groups

`common_specs` covers memory, bandwidth, power, form factor, host interface,
interconnect, software stack, and release information.

`compute_specs` covers FP64, FP32, TF32, BF16, FP16, FP8, INT8, TOPS/FLOPS,
matrix engines, sparse performance, and supported precision modes.

`role_specific_specs` covers DPU/IPU networking and offload fields, FPGA logic
resources, TPU deployment details, NPU/DSA compiler and operator support, and
cloud offering aggregate fields.

# Unit Policy

Resolved fields use canonical units from `spec-fields.yaml`. Observations can
preserve source wording in notes, but normalized values should use canonical
units such as `GB`, `TB/s`, `W`, `TFLOPS`, `TOPS`, `Gb/s`, and `count`.

# Citations

- ../../data/compute_accelerators/schema/accelerator-scopes.yaml
- ../../data/compute_accelerators/schema/spec-fields.yaml
```

- [ ] **Step 3: Create catalog project page**

Create `personal-wiki/domains/ai_infra/wiki/projects/compute-accelerator-spec-catalog.md` with:

```markdown
---
type: Project
title: Compute Accelerator Spec Catalog
description: Structured catalog for source-backed GPU, NPU, TPU, DPU, IPU, FPGA, DSA, and AI ASIC specifications.
domain: ai_infra
status: reviewed
aliases:
  - accelerator spec catalog
  - compute accelerator catalog
tags:
  - accelerators
  - catalog
  - specs
source_refs:
  - ../../data/compute_accelerators/README.md
  - ../../data/compute_accelerators/skus/sample-skus.yaml
  - ../../data/compute_accelerators/observations/sample-observations.yaml
  - ../../data/compute_accelerators/resolved/sample-resolved-specs.yaml
---

# Summary

The compute accelerator spec catalog is the structured facts layer for
accelerator parameters in the `ai_infra` domain. It stores sample SKUs,
source-backed observations, and resolved fields with provenance.

# Current Coverage

The seed catalog validates the schema across representative GPU, TPU, DPU,
FPGA, cloud custom accelerator, and AI ASIC records. It intentionally leaves
incomplete public fields unresolved instead of inventing missing values.

# Data Flow

Raw evidence and crawler snapshots produce candidate records. Reviewed
candidates become observations. Resolved specs point back to observations and
preserve conflict status, confidence, and update timestamps.

# Validation

Run:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators
```

# Citations

- ../../data/compute_accelerators/README.md
- ../../data/compute_accelerators/skus/sample-skus.yaml
- ../../data/compute_accelerators/observations/sample-observations.yaml
- ../../data/compute_accelerators/resolved/sample-resolved-specs.yaml
```

- [ ] **Step 4: Create crawler project page**

Create `personal-wiki/domains/ai_infra/wiki/projects/compute-accelerator-crawler.md` with:

```markdown
---
type: Project
title: Compute Accelerator Crawler
description: Crawler source profile conventions for accelerator specification discovery and candidate extraction.
domain: ai_infra
status: reviewed
aliases:
  - accelerator crawler
  - accelerator source profiles
tags:
  - accelerators
  - crawler
  - ingestion
source_refs:
  - ../../data/compute_accelerators/candidates/README.md
  - ../../data/compute_accelerators/sources/source-registry.yaml
---

# Summary

Compute accelerator crawler profiles discover source changes and write raw
snapshots plus candidate structured records. They do not directly overwrite
resolved specifications.

# Profile Metadata

Each accelerator source profile includes source rank, accelerator scope,
extract mode, vendor hint, and auto-resolve policy. `extract_mode:
specs_candidate` means the crawler writes candidate data for later validation.

# Review Boundary

High-trust official sources can produce observations when extraction is clear.
Cloud sources update cloud offering fields. Third-party sources stay pending
review and cannot auto-resolve without `reviewed_by`.

# Citations

- ../../data/compute_accelerators/candidates/README.md
- ../../data/compute_accelerators/sources/source-registry.yaml
```

- [ ] **Step 5: Rebuild domain index**

Run:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki index ai_infra
```

Expected: command prints the index path and updates `personal-wiki/domains/ai_infra/wiki/index.md`.

- [ ] **Step 6: Validate wiki pages**

Run:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra
```

Expected:

```text
No validation issues
```

- [ ] **Step 7: Commit Task 4**

Run:

```bash
git add \
  personal-wiki/domains/ai_infra/wiki/references/compute-accelerator-spec-sources.md \
  personal-wiki/domains/ai_infra/wiki/references/compute-accelerator-field-glossary.md \
  personal-wiki/domains/ai_infra/wiki/projects/compute-accelerator-spec-catalog.md \
  personal-wiki/domains/ai_infra/wiki/projects/compute-accelerator-crawler.md \
  personal-wiki/domains/ai_infra/wiki/index.md
git commit -m "docs(wiki): document accelerator spec catalog"
```

Expected: commit succeeds and includes only Task 4 files.

## Task 5: Extend Crawler Profile Metadata Validation

**Files:**
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/profiles.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/tests/test_db_profiles.py`

- [ ] **Step 1: Add failing profile metadata tests**

Append these tests to `personal-wiki/apps/crawler_workbench/backend/tests/test_db_profiles.py`:

```python
def test_yaml_profile_accepts_compute_accelerator_metadata(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
sources:
  - id: compute-accelerators-nvidia-h200
    name: NVIDIA H200 accelerator specs
    type: web
    target_domain: ai_infra
    url: https://www.nvidia.com/en-us/data-center/h200/
    trust_level: trusted
    schedule: weekly
    auto_ingest: false
    auth_required: false
    topic: NVIDIA H200 accelerator specs
    source_rank: S1
    accelerator_scope:
      - gpu
    extract_mode: specs_candidate
    vendor_hint: nvidia
    auto_resolve: false
""",
        encoding="utf-8",
    )
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        with transaction(db):
            mirror_profiles(db, load_profiles_from_yaml(yaml_path))
        row = db.execute(
            "select config_json from source_profiles where id = 'compute-accelerators-nvidia-h200'"
        ).fetchone()

    assert row["config_json"] == (
        '{"accelerator_scope": ["gpu"], "auto_resolve": false, '
        '"extract_mode": "specs_candidate", "source_rank": "S1", "vendor_hint": "nvidia"}'
    )


def test_yaml_profile_rejects_invalid_accelerator_scope(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
sources:
  - id: bad-accelerator-scope
    name: Bad accelerator scope
    type: web
    target_domain: ai_infra
    url: https://example.com
    trust_level: trusted
    schedule: weekly
    auto_ingest: false
    auth_required: false
    topic: bad accelerator scope
    source_rank: S1
    accelerator_scope:
      - quantum
    extract_mode: specs_candidate
    auto_resolve: false
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid accelerator_scope"):
        load_profiles_from_yaml(yaml_path)


def test_yaml_profile_rejects_s5_auto_resolve(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
sources:
  - id: bad-s5-auto-resolve
    name: Bad S5 auto resolve
    type: web
    target_domain: ai_infra
    url: https://example.com
    trust_level: untrusted
    schedule: weekly
    auto_ingest: false
    auth_required: false
    topic: bad S5 auto resolve
    source_rank: S5
    accelerator_scope:
      - gpu
    extract_mode: specs_candidate
    auto_resolve: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="S5 profiles cannot auto_resolve"):
        load_profiles_from_yaml(yaml_path)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_db_profiles.py
```

Expected: FAIL because accelerator metadata is not validated yet.

- [ ] **Step 3: Implement accelerator metadata validation**

Modify `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/profiles.py`.

Add constants after `PROFILE_STORAGE_KEYS`:

```python
ACCELERATOR_SOURCE_RANKS = {"S1", "S2", "S3", "S4", "S5"}
ACCELERATOR_SCOPES = {"gpu", "npu", "tpu", "dpu", "ipu", "fpga", "dsa", "ai_asic"}
ACCELERATOR_EXTRACT_MODES = {"specs_candidate", "snapshot_only", "manual_probe"}
```

In `load_profiles_from_yaml`, after `validate_profile_domain(profile)`, add:

```python
        validate_accelerator_metadata(profile)
```

In `mirror_profiles`, after `validate_profile_domain(profile)`, add:

```python
        validate_accelerator_metadata(profile)
```

Add this function after `validate_profile_domain`:

```python
def validate_accelerator_metadata(profile: dict[str, Any]) -> None:
    profile_id = profile.get("id", "<unknown>")
    has_accelerator_metadata = any(
        key in profile
        for key in ("source_rank", "accelerator_scope", "extract_mode", "auto_resolve")
    )
    if not has_accelerator_metadata:
        return

    source_rank = profile.get("source_rank")
    if source_rank not in ACCELERATOR_SOURCE_RANKS:
        raise ValueError(f"profile {profile_id} invalid source_rank: {source_rank}")

    scopes = profile.get("accelerator_scope")
    if not isinstance(scopes, list) or not scopes:
        raise ValueError(f"profile {profile_id} accelerator_scope must be a non-empty list")
    invalid_scopes = sorted(str(scope) for scope in scopes if scope not in ACCELERATOR_SCOPES)
    if invalid_scopes:
        raise ValueError(
            f"profile {profile_id} invalid accelerator_scope: {', '.join(invalid_scopes)}"
        )

    extract_mode = profile.get("extract_mode")
    if extract_mode not in ACCELERATOR_EXTRACT_MODES:
        raise ValueError(f"profile {profile_id} invalid extract_mode: {extract_mode}")

    auto_resolve = profile.get("auto_resolve")
    if not isinstance(auto_resolve, bool):
        raise ValueError(f"profile {profile_id} key auto_resolve must be a boolean")
    if source_rank == "S5" and auto_resolve:
        raise ValueError(f"profile {profile_id} S5 profiles cannot auto_resolve")
```

- [ ] **Step 4: Run profile tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_db_profiles.py
```

Expected: PASS.

- [ ] **Step 5: Commit Task 5**

Run:

```bash
git add \
  personal-wiki/apps/crawler_workbench/backend/crawler_workbench/profiles.py \
  personal-wiki/apps/crawler_workbench/backend/tests/test_db_profiles.py
git commit -m "feat(crawler): validate accelerator source metadata"
```

Expected: commit succeeds and includes only Task 5 files.

## Task 6: Add Compute Accelerator Source Profiles

**Files:**
- Modify: `personal-wiki/apps/crawler_workbench/config/sources.example.yaml`

- [ ] **Step 1: Append accelerator source profiles**

Append this block to `personal-wiki/apps/crawler_workbench/config/sources.example.yaml`:

```yaml
- id: compute-accelerators-nvidia-h200
  name: NVIDIA H200 accelerator specs
  type: web
  target_domain: ai_infra
  url: https://www.nvidia.com/en-us/data-center/h200/
  trust_level: trusted
  schedule: weekly
  auto_ingest: false
  auth_required: false
  baseline_on_first_run: true
  topic: NVIDIA H200 accelerator specifications
  source_rank: S1
  accelerator_scope:
  - gpu
  extract_mode: specs_candidate
  vendor_hint: nvidia
  auto_resolve: false
- id: compute-accelerators-amd-mi325x
  name: AMD Instinct MI325X accelerator specs
  type: web
  target_domain: ai_infra
  url: https://www.amd.com/en/products/accelerators/instinct/mi300/mi325x.html
  trust_level: trusted
  schedule: weekly
  auto_ingest: false
  auth_required: false
  baseline_on_first_run: true
  topic: AMD Instinct MI325X accelerator specifications
  source_rank: S1
  accelerator_scope:
  - gpu
  extract_mode: specs_candidate
  vendor_hint: amd
  auto_resolve: false
- id: compute-accelerators-intel-gaudi-3
  name: Intel Gaudi 3 accelerator white paper
  type: web
  target_domain: ai_infra
  url: https://cdrdv2-public.intel.com/817486/gaudi-3-ai-accelerator-white-paper.pdf
  trust_level: trusted
  schedule: monthly
  auto_ingest: false
  auth_required: false
  baseline_on_first_run: true
  topic: Intel Gaudi 3 accelerator specifications
  source_rank: S1
  accelerator_scope:
  - ai_asic
  extract_mode: specs_candidate
  vendor_hint: intel
  auto_resolve: false
- id: compute-accelerators-nvidia-bluefield-3
  name: NVIDIA BlueField-3 DPU specs
  type: web
  target_domain: ai_infra
  url: https://www.nvidia.com/en-us/networking/products/data-processing-unit/
  trust_level: trusted
  schedule: monthly
  auto_ingest: false
  auth_required: false
  baseline_on_first_run: true
  topic: NVIDIA BlueField-3 DPU specifications
  source_rank: S1
  accelerator_scope:
  - dpu
  extract_mode: specs_candidate
  vendor_hint: nvidia
  auto_resolve: false
- id: compute-accelerators-aws-trn2
  name: AWS Trn2 Trainium2 instance specs
  type: web
  target_domain: ai_infra
  url: https://aws.amazon.com/ec2/instance-types/trn2/
  trust_level: trusted
  schedule: weekly
  auto_ingest: false
  auth_required: false
  baseline_on_first_run: true
  topic: AWS Trainium2 cloud accelerator offerings
  source_rank: S2
  accelerator_scope:
  - ai_asic
  extract_mode: specs_candidate
  vendor_hint: aws
  auto_resolve: false
- id: compute-accelerators-google-tpu
  name: Google Cloud TPU documentation
  type: web
  target_domain: ai_infra
  url: https://cloud.google.com/tpu/docs
  trust_level: trusted
  schedule: weekly
  auto_ingest: false
  auth_required: false
  baseline_on_first_run: true
  topic: Google Cloud TPU accelerator offerings
  source_rank: S2
  accelerator_scope:
  - tpu
  extract_mode: specs_candidate
  vendor_hint: google
  auto_resolve: false
- id: compute-accelerators-mlperf-training
  name: MLCommons training benchmark results
  type: web
  target_domain: ai_infra
  url: https://mlcommons.org/benchmarks/training/
  trust_level: trusted
  schedule: monthly
  auto_ingest: false
  auth_required: false
  baseline_on_first_run: true
  topic: MLPerf training benchmark accelerator results
  source_rank: S3
  accelerator_scope:
  - gpu
  - tpu
  - ai_asic
  extract_mode: specs_candidate
  vendor_hint: mlcommons
  auto_resolve: false
- id: compute-accelerators-techpowerup-gpu-db
  name: TechPowerUp GPU database monitor
  type: web
  target_domain: ai_infra
  url: https://www.techpowerup.com/gpu-specs/
  trust_level: untrusted
  schedule: monthly
  auto_ingest: false
  auth_required: false
  baseline_on_first_run: true
  topic: Third-party GPU database candidate monitor
  source_rank: S5
  accelerator_scope:
  - gpu
  extract_mode: specs_candidate
  vendor_hint: techpowerup
  auto_resolve: false
```

- [ ] **Step 2: Validate sources YAML through profile loader**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. python - <<'PY'
from pathlib import Path
from crawler_workbench.profiles import load_profiles_from_yaml

path = Path("../config/sources.example.yaml")
profiles = load_profiles_from_yaml(path)
accelerator_profiles = [
    profile for profile in profiles if profile["id"].startswith("compute-accelerators-")
]
print(len(accelerator_profiles))
print(sorted(profile["id"] for profile in accelerator_profiles))
PY
```

Expected: `8` and the eight `compute-accelerators-*` IDs.

- [ ] **Step 3: Run profile tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_db_profiles.py
```

Expected: PASS.

- [ ] **Step 4: Commit Task 6**

Run:

```bash
git add personal-wiki/apps/crawler_workbench/config/sources.example.yaml
git commit -m "chore(crawler): add accelerator source profiles"
```

Expected: commit succeeds and includes only Task 6 file.

## Task 7: Final Validation and Task Bookkeeping

**Files:**
- Modify: `tasks.json`
- Modify: `progress.md`

- [ ] **Step 1: Run accelerator catalog validator**

Run:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators
```

Expected:

```text
No accelerator catalog validation issues
```

- [ ] **Step 2: Run wiki validation**

Run:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra
```

Expected:

```text
No validation issues
```

- [ ] **Step 3: Run focused Python tests**

Run:

```bash
PYTHONPATH=personal-wiki/tests pytest -q personal-wiki/tests/test_accelerator_catalog.py
```

Expected: PASS.

- [ ] **Step 4: Run focused crawler profile tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_db_profiles.py
```

Expected: PASS.

- [ ] **Step 5: Add task entry to `tasks.json`**

Modify `tasks.json` by inserting this task at the top of the `tasks` array, preserving existing tasks:

```json
{
  "id": "compute-accelerator-spec-catalog-01",
  "title": "Build compute accelerator spec catalog seed",
  "description": "Create the structured accelerator spec catalog, curated wiki pages, crawler source metadata, and validation checks for GPU, NPU, TPU, DPU, IPU, FPGA, DSA, and AI ASIC coverage.",
  "status": "done",
  "priority": "high",
  "blocked_by": "",
  "verify": "python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators && python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra && PYTHONPATH=personal-wiki/tests pytest -q personal-wiki/tests/test_accelerator_catalog.py && cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_db_profiles.py",
  "requires_eval": false,
  "eval_policy": {
    "task_level_required": true,
    "final_level_required": false,
    "task_scope": "local_repo_and_personal_wiki",
    "final_scope": "report_and_artifacts",
    "max_task_eval_attempts": 3,
    "max_final_eval_attempts": 2
  }
}
```

Also update top-level `last_updated` to `"2026-06-27"`. Do not change unrelated task statuses.

- [ ] **Step 6: Add progress record**

Prepend this record below the opening separator in `progress.md`:

```markdown
## 2026-06-27 Compute Accelerator Spec Catalog

- Built the seed structured catalog under `personal-wiki/domains/ai_infra/data/compute_accelerators/`.
- Added curated wiki pages for source policy, field glossary, catalog overview, and crawler conventions.
- Added `validate-accelerators` to check schema, source refs, observations, resolved fields, and S5 review policy.
- Added crawler source metadata validation and sample accelerator source profiles.
- Verification:
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators`
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra`
  - `PYTHONPATH=personal-wiki/tests pytest -q personal-wiki/tests/test_accelerator_catalog.py`
  - `cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_db_profiles.py`
```

- [ ] **Step 7: Commit Task 7**

Run:

```bash
git add tasks.json progress.md
git commit -m "chore: record accelerator catalog task"
```

Expected: commit succeeds and includes only `tasks.json` and `progress.md`.

## Final Verification

Run the complete verification set:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra
PYTHONPATH=personal-wiki/tests pytest -q personal-wiki/tests/test_accelerator_catalog.py
(cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_db_profiles.py)
git status --short
```

Expected:

- Accelerator validator prints `No accelerator catalog validation issues`.
- Wiki validator prints `No validation issues`.
- Both pytest commands pass.
- `git status --short` may still show unrelated pre-existing dirty files, but no unstaged or staged files from this plan should remain.

## Implementation Notes

- Use `apply_patch` for manual edits.
- Do not stage unrelated dirty files.
- Do not fetch private or authenticated sources.
- Do not use crawler source profiles to auto-resolve final specs in this seed implementation.
- If an official source value is uncertain, omit the resolved field and keep only source registry or candidate notes.
