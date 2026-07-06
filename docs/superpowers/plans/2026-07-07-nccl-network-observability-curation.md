# NCCL Network Observability Curation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Curate the local NCCL/NVIDIA technical blog captures into source-backed ai_infra wiki, coverage state, and loop evidence for run `ai-infra-expansion-2026-07-06-r3` task 2.

**Architecture:** Reuse existing raw captures under `personal-wiki/domains/ai_infra/raw/crawler/nccl-technical-blog/` as the fact layer. Add one durable reference page, link it from NCCL and the coverage map, then update machine-readable coverage state and verification manifests.

**Tech Stack:** Markdown wiki pages with YAML frontmatter, JSON machine state, Python wiki CLI validation, harness loop contract validators.

## Global Constraints

- Do not fetch or crawl new external sources.
- Do not touch the pre-existing untracked `20260706` compute accelerator captures.
- Do not change crawler, frontend, loop dashboard, or harness code unless a blocking defect appears.
- Do not run git commit or fill the generator `commit` field.
- Keep `data-rag-vector` as a remaining gap.

---

### Task 1: Gap Proof and Curated Reference

**Files:**
- Create: `personal-wiki/domains/ai_infra/manifest-ai-infra-expansion-2026-07-06-r3-task-2-gap-proof.json`
- Create: `personal-wiki/domains/ai_infra/wiki/references/nccl-technical-blog-network-observability.md`
- Modify: `personal-wiki/domains/ai_infra/wiki/projects/nccl.md`
- Modify: `personal-wiki/domains/ai_infra/wiki/references/ai-infra-coverage-map.md`

**Interfaces:**
- Consumes: local NCCL raw captures selected in `.codex/loop-runs/ai-infra-expansion-2026-07-06-r3/planner-output.json`
- Produces: a reference page path usable by `coverage-map.json`, `loop-state.json`, and search/frontend visibility checks

- [ ] **Step 1: Write task-2 gap proof**

Create a JSON object with `task_id`, `layer`, `candidate`, `local_checks`, `gap_reason`, `planned_outputs`, selected raw paths, and duplicate findings. Verify with:

```bash
python3 -m json.tool personal-wiki/domains/ai_infra/manifest-ai-infra-expansion-2026-07-06-r3-task-2-gap-proof.json >/dev/null
python3 - <<'PY'
from scripts.harness_ai_infra_evidence import validate_gap_proof_file
findings = validate_gap_proof_file(
    'personal-wiki/domains/ai_infra/manifest-ai-infra-expansion-2026-07-06-r3-task-2-gap-proof.json',
    expected_task_id='ai-infra-expansion-2026-07-06-r3-task-2',
)
if findings:
    raise SystemExit('\n'.join(findings))
PY
```

- [ ] **Step 2: Add one focused reference page**

Write `nccl-technical-blog-network-observability.md` with `source_refs` to the local NCCL technical blog captures and concise sections for Inspector/Prometheus, NCCL 2.24 RAS/NIC Fusion, Spectrum-X/RoCE convergence, NVBandwidth/SHARP, and NCCL 2.22 cost estimation.

- [ ] **Step 3: Link the page**

Add the reference page to `wiki/projects/nccl.md` and `wiki/references/ai-infra-coverage-map.md`, preserving existing source refs and citations.

### Task 2: Machine State and Verification Evidence

**Files:**
- Modify: `personal-wiki/domains/ai_infra/coverage-map.json`
- Modify: `personal-wiki/domains/ai_infra/loop-state.json`
- Modify: `personal-wiki/domains/ai_infra/ingest.md`
- Modify: `personal-wiki/domains/ai_infra/wiki/index.md`
- Create: `personal-wiki/domains/ai_infra/manifest-ai-infra-expansion-2026-07-06-r3-task-2-verification.json`
- Modify: `.codex/loop-runs/ai-infra-expansion-2026-07-06-r3/required-evidence-manifest.json`
- Create: `.codex/loop-runs/ai-infra-expansion-2026-07-06-r3/generator-result.json`

**Interfaces:**
- Consumes: reference page from Task 1 and planner `verify_commands`
- Produces: generator result payload satisfying `scripts.harness_loop_contracts.validate_generator_result_payload`

- [ ] **Step 1: Update coverage and loop state**

Add the new curated page and raw evidence to `training-distributed`, `eval-observability-reliability`, `security-governance-cost`, and `network-storage-cluster`. Keep remaining gaps in `candidate_backlog`, especially `data-rag-vector`.

- [ ] **Step 2: Rebuild and validate**

Run:

```bash
python3 personal-wiki/tools/wiki_cli/cli.py --root personal-wiki index ai_infra
python3 personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra
```

- [ ] **Step 3: Run planner verification commands**

Run the JSON validators, gap proof validator, `git diff --check`, a targeted sensitive-pattern scan over changed files, an autonomous scope check, and live curl checks for backend/frontend/dashboard if services are available.

- [ ] **Step 4: Write result artifacts**

Write the task-2 verification manifest, refresh required evidence manifest with task-2 artifact paths and stable semantic evidence ids, and write `generator-result.json` with non-empty `verify_results` and an empty `commit`.
