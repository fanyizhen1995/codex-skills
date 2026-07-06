# AI Infra Meta Loop Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the runtime and evaluator gates required before the AI Infra Meta Loop can automatically move from demand-development fixes into autonomous `ai_infra` knowledge expansion.

**Architecture:** Keep the existing harness JSON-file state machine and add focused helpers for policy loading, coverage state, gap proof validation, required evidence checks, service freshness evidence, and meta-loop transition. The orchestrator remains deterministic around agent calls: agents may create artifacts, but the harness validates scope, evidence, dirty paths, supply-chain requirements, and transition gates before committing or continuing.

**Tech Stack:** Python standard library, existing `unittest` harness tests, existing JSON contract validators, existing crawler workbench and loop dashboard health endpoints.

## Global Constraints

- The parent Meta Loop runs Phase A demand-development first, then automatically transitions to Phase B autonomous knowledge expansion in the same feature branch/worktree without waiting for `main` merge.
- Final merge to `main` remains human-gated.
- Phase A must implement expanded policy runtime loading, coverage map state and no-action gate, gap proof/dedupe validator, required evidence gate, AI infra evaluator scenario, service availability/dashboard/crawler freshness gates, and Meta Loop transition.
- Formal AI infra expansion uses `docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json`.
- The expanded policy must allow repo-wide repair paths while still denying secrets, credentials, `.codex/**`, `.worktrees/**`, `generated/**`, local logs, pids, caches, and build outputs.
- Every AI infra candidate task must have a gap proof and duplicate checks before Generator work.
- `stopped_no_action` for `ai_infra` must be based on all 8 coverage layers, not merely non-empty `known_sources`.
- Each round must prove Crawler Workbench backend `8765`, Crawler Workbench frontend `5173`, and Loop Dashboard `8766` availability or carry explicit blocked evidence.
- New knowledge visibility must be verified through backend API/search, frontend, and Loop Dashboard freshness evidence.
- Services must stay online for remote inspection; only restart when code/config changes require it and record the reason.
- Do not commit `.codex/*.log`, pid files, `generated/`, `.worktrees/`, credentials, private tokens, browser caches, Python caches, Node caches, build outputs, or unrelated crawler raw/runtime artifacts.
- Use TDD for production code changes: write focused failing tests, verify RED, implement minimal code, verify GREEN.

---

### Task 1: Expanded Policy Runtime Loading

**Files:**
- Modify: `scripts/harness_loop_contracts.py`
- Modify: `scripts/harness_loop_autonomous.py`
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/tests/test_harness_loop_contracts.py`
- Modify: `scripts/tests/test_harness_loop_autonomous.py`
- Modify: `scripts/tests/test_harness_loop_orchestrator.py`
- Modify: `docs/harness/planner-generator-evaluator-loop.md`

**Interfaces:**
- Produces: `load_loop_policy(repo_root: Path | str, policy_file: str) -> dict[str, Any]`
- Produces: `policy_patterns_for_run(run: Mapping[str, Any], *, domain: str) -> tuple[list[str], list[str], list[str]]`
- Produces: `run.json` optional fields `policy_file`, `manual_confirm_paths`, `required_evidence`
- Consumes: existing `validate_loop_policy_payload`, `create_preflight_run`, `run_autonomous`, `_commit_autonomous_changes`

- [ ] **Step 1: Write failing contract tests**

Add tests that assert a run payload may carry `policy_file`, `manual_confirm_paths`, and `required_evidence`, and that invalid policy fixture paths or mismatched policies are rejected by the loader.

Run: `python3 -m unittest scripts.tests.test_harness_loop_contracts -v`

Expected RED: tests fail because `load_loop_policy` and optional run policy metadata are not implemented.

- [ ] **Step 2: Write failing orchestrator tests**

Add tests that create an autonomous preflight with:

```python
policy_file = "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json"
payload = create_preflight_run(
    repo_root=repo_root,
    mode="autonomous-knowledge",
    requirement="Expand ai_infra",
    run_id="expanded-run",
    confirm=True,
    domain="ai_infra",
    policy_file=policy_file,
)
self.assertEqual(payload["policy_file"], policy_file)
self.assertIn("**", payload["allowed_paths"])
self.assertIn(".codex/**", payload["denylist_paths"])
self.assertIn("service availability evidence", " ".join(payload["required_evidence"]))
self.assertEqual(payload["limits"]["max_rounds_per_invocation"], 4)
```

Run: `python3 -m unittest scripts.tests.test_harness_loop_orchestrator.HarnessLoopOrchestratorTests.test_create_preflight_run_records_expanded_policy_fixture -v`

Expected RED: `create_preflight_run()` does not accept `policy_file`.

- [ ] **Step 3: Write failing scope tests**

Add tests for `policy_patterns_for_run()`:

```python
allowed, denied, manual = policy_patterns_for_run(
    {
        "allowed_paths": ["**"],
        "denylist_paths": [".codex/**", "generated/**"],
        "manual_confirm_paths": [],
    },
    domain="ai_infra",
)
result = check_autonomous_scope(["scripts/harness_loop_orchestrator.py"], allowed, denied, manual)
self.assertTrue(result.allowed)
self.assertFalse(check_autonomous_scope([".codex/secret.log"], allowed, denied, manual).allowed)
```

Run: `python3 -m unittest scripts.tests.test_harness_loop_autonomous.HarnessLoopAutonomousTests.test_policy_patterns_allow_repo_wide_repairs_but_keep_denylist -v`

Expected RED: `policy_patterns_for_run` does not exist.

- [ ] **Step 4: Implement policy fixture loading**

Implement `load_loop_policy()` so it accepts only repo-relative JSON files inside the repository, rejects absolute paths and `..`, validates the fixture with `validate_loop_policy_payload()`, and returns a copy.

Update `create_preflight_run()` and CLI `preflight` with `--policy-file`. When present, merge policy fixture fields into `run.json`:

- `allowed_paths`
- `denylist_paths`
- `manual_confirm_paths`
- `limits` merged over `default_limits()`
- `required_evidence`
- `policy_file`

Reject a policy fixture whose normalized `policy` differs from `mode`.

- [ ] **Step 5: Use run policy for autonomous planning and commits**

Implement `policy_patterns_for_run()` in `scripts/harness_loop_autonomous.py`. Default to existing conservative allow/manual/deny patterns when run fields are empty. Update `_run_fake_autonomous_planner()` and `_commit_autonomous_changes()` to use patterns from the current run instead of only the hardcoded conservative scope.

Keep dependency supply-chain checks independent: even if `allowed_paths` is `["**"]`, dependency paths still require necessity and verification evidence.

- [ ] **Step 6: Verify GREEN**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_autonomous scripts.tests.test_harness_loop_orchestrator -v
python3 - <<'PY'
from pathlib import Path
from scripts.harness_loop_contracts import read_json_file, validate_loop_policy_payload
for path in Path("docs/harness/loop-policies").glob("*.json"):
    validate_loop_policy_payload(read_json_file(path))
PY
git diff --check
```

Expected GREEN: all commands exit `0`.

- [ ] **Step 7: Commit**

```bash
git add scripts/harness_loop_contracts.py scripts/harness_loop_autonomous.py scripts/harness_loop_orchestrator.py scripts/tests/test_harness_loop_contracts.py scripts/tests/test_harness_loop_autonomous.py scripts/tests/test_harness_loop_orchestrator.py docs/harness/planner-generator-evaluator-loop.md
git commit -m "feat(harness): load expanded autonomous loop policies"
```

### Task 2: AI Infra Coverage Map And No-Action Gate

**Files:**
- Modify: `scripts/harness_loop_contracts.py`
- Modify: `scripts/harness_loop_autonomous.py`
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/tests/test_harness_loop_contracts.py`
- Modify: `scripts/tests/test_harness_loop_autonomous.py`
- Modify: `scripts/tests/test_harness_loop_orchestrator.py`
- Modify: `docs/harness/planner-generator-evaluator-loop.md`

**Interfaces:**
- Produces: `AI_INFRA_COVERAGE_LAYERS: tuple[str, ...]`
- Produces: `create_default_coverage_map(domain: str, domain_goal: str) -> dict[str, Any]`
- Produces: `load_or_create_coverage_map(repo_root: Path | str, domain: str, domain_goal: str) -> dict[str, Any]`
- Produces: `write_coverage_map(repo_root: Path | str, domain: str, payload: Mapping[str, Any]) -> Path`
- Produces: `validate_coverage_map_payload(payload: dict[str, Any]) -> None`
- Modifies: `decide_no_action(state, now=None, coverage_map=None)`

- [ ] **Step 1: Write failing coverage schema tests**

Add tests that a valid `ai_infra` coverage map contains exactly these layers:

```python
[
    "training-distributed",
    "inference-runtime",
    "orchestration-scheduling",
    "data-rag-vector",
    "eval-observability-reliability",
    "security-governance-cost",
    "hardware-accelerator",
    "network-storage-cluster",
]
```

Each layer must include `status`, `covered_pages`, `raw_evidence`, `candidate_gaps`, `blocked_reason`, `last_scanned_at`, and `notes`.

Run: `python3 -m unittest scripts.tests.test_harness_loop_contracts.HarnessLoopContractsTests.test_validate_coverage_map_payload_accepts_ai_infra_layers -v`

Expected RED: `validate_coverage_map_payload` does not exist.

- [ ] **Step 2: Write failing no-action tests**

Add tests that `decide_no_action()` rejects:

- missing `coverage_map` for `ai_infra`
- missing layer
- layer with `candidate_gaps`
- layer with stale `last_scanned_at`
- no `no_action_evidence` entry referencing `coverage-map`

Run: `python3 -m unittest scripts.tests.test_harness_loop_autonomous.HarnessLoopAutonomousTests.test_decide_no_action_requires_ai_infra_coverage_map -v`

Expected RED: current `decide_no_action()` ignores coverage maps.

- [ ] **Step 3: Write failing orchestrator test**

Add a test that seeds an `ai_infra` loop-state with legacy no-action evidence but no coverage map, then runs `run_autonomous()` with fake drivers.

Expected result:

```python
self.assertNotEqual(status["phase"], "stopped_no_action")
self.assertEqual(status["phase"], "stopped_blocked")
self.assertEqual(load_run(repo_root, "ai-run")["next_action"], "inspect_ai_infra_coverage_map")
```

Run: `python3 -m unittest scripts.tests.test_harness_loop_orchestrator.HarnessLoopOrchestratorTests.test_run_autonomous_requires_ai_infra_coverage_map_before_no_action -v`

Expected RED: current fake planner stops at `stopped_no_action`.

- [ ] **Step 4: Implement coverage map helpers**

Implement the coverage map schema validator in `scripts/harness_loop_contracts.py`, and add default/load/write helpers in `scripts/harness_loop_autonomous.py`. Store coverage at:

```text
personal-wiki/domains/<domain>/coverage-map.json
```

For non-`ai_infra` domains, keep existing no-action behavior unless a coverage map is explicitly supplied.

- [ ] **Step 5: Wire no-action through coverage map**

Update `_run_fake_autonomous_planner()` and `_stop_if_autonomous_no_action()` to load `coverage-map.json` for `ai_infra`. If the file is missing or invalid, stop as `stopped_blocked` with `next_action="inspect_ai_infra_coverage_map"` and write `.codex/loop-runs/<run-id>/coverage-map-result.json`.

If the coverage map is valid but actionable gaps remain, do not stop no-action; continue planning or stop budget as before.

- [ ] **Step 6: Update fake generator no-action evidence**

When fake autonomous generator clears the candidate backlog for `ai_infra`, write a complete synthetic coverage map so existing Phase 3 smoke can still reach `stopped_no_action` after one task.

- [ ] **Step 7: Verify GREEN**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_autonomous scripts.tests.test_harness_loop_orchestrator -v
git diff --check
```

Expected GREEN: all commands exit `0`.

- [ ] **Step 8: Commit**

```bash
git add scripts/harness_loop_contracts.py scripts/harness_loop_autonomous.py scripts/harness_loop_orchestrator.py scripts/tests/test_harness_loop_contracts.py scripts/tests/test_harness_loop_autonomous.py scripts/tests/test_harness_loop_orchestrator.py docs/harness/planner-generator-evaluator-loop.md
git commit -m "feat(harness): require ai infra coverage maps"
```

### Task 3: Gap Proof And Deduplication Validator

**Files:**
- Create: `scripts/harness_ai_infra_evidence.py`
- Create: `scripts/tests/test_harness_ai_infra_evidence.py`
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `docs/harness/planner-generator-evaluator-loop.md`

**Interfaces:**
- Produces: `canonicalize_url(url: str) -> str`
- Produces: `identity_key_for_candidate(candidate: Mapping[str, Any]) -> str`
- Produces: `validate_gap_proof_payload(payload: Mapping[str, Any]) -> list[str]`
- Produces: `validate_gap_proof_file(path: Path | str) -> list[str]`
- Produces artifact: `.codex/loop-runs/<run-id>/gap-proof-result.json`

- [ ] **Step 1: Write failing canonical identity tests**

Add tests for:

```python
self.assertEqual(
    canonicalize_url("HTTPS://Docs.VLLM.AI/en/latest/foo/?utm_source=x#section"),
    "https://docs.vllm.ai/en/latest/foo/#section",
)
self.assertEqual(identity_key_for_candidate({"source_type": "github_issue", "owner": "kubernetes", "repo": "kubernetes", "number": 123}), "github:kubernetes/kubernetes#123")
self.assertEqual(identity_key_for_candidate({"source_type": "paper", "arxiv_id": "2401.01234v2"}), "arxiv:2401.01234")
self.assertEqual(identity_key_for_candidate({"source_type": "hardware", "vendor": "NVIDIA", "model": "H200 SXM", "sku_or_memory_variant": "141GB"}), "hardware:nvidia:h200-sxm:141gb")
```

Run: `python3 -m unittest scripts.tests.test_harness_ai_infra_evidence -v`

Expected RED: module does not exist.

- [ ] **Step 2: Write failing gap proof validation tests**

Add tests that `validate_gap_proof_payload()` requires:

- `task_id`
- `layer`
- `candidate.title`
- `candidate.source_type`
- `candidate.identity_key`
- `local_checks.raw_manifest_scan`
- `local_checks.wiki_search`
- `local_checks.domain_index_scan`
- `gap_reason`
- non-empty `planned_outputs`

Run: `python3 -m unittest scripts.tests.test_harness_ai_infra_evidence.HarnessAiInfraEvidenceTests.test_validate_gap_proof_requires_duplicate_checks -v`

Expected RED: validator missing.

- [ ] **Step 3: Write failing orchestrator artifact test**

Add a test that uses expanded policy required evidence and a generator result without any gap proof artifact. `_commit_autonomous_changes()` must stop with `next_action="inspect_required_evidence"`.

Run: `python3 -m unittest scripts.tests.test_harness_loop_orchestrator.HarnessLoopOrchestratorTests.test_run_autonomous_blocks_expanded_policy_without_gap_proof -v`

Expected RED: no required evidence gate exists yet.

- [ ] **Step 4: Implement validator module**

Implement URL normalization with `urllib.parse`, remove common tracking query keys (`utm_*`, `fbclid`, `gclid`), lowercase scheme/host, preserve meaningful fragments, and normalize paper/hardware keys as described in the spec.

`validate_gap_proof_payload()` returns a list of findings. Empty list means pass. It must not raise for ordinary validation failures; reserve raises for unreadable JSON in `validate_gap_proof_file()`.

- [ ] **Step 5: Wire gap proof evidence into autonomous commit gate**

When `run["required_evidence"]` contains any string with `gap proof`, `_commit_autonomous_changes()` must look for either:

- `.codex/loop-runs/<run-id>/gap-proofs/<task-id>.json`
- a `required-evidence-manifest.json` entry whose evidence id contains `gap-proof`

Write `.codex/loop-runs/<run-id>/gap-proof-result.json` with status `pass` or `blocked`.

- [ ] **Step 6: Verify GREEN**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_ai_infra_evidence scripts.tests.test_harness_loop_orchestrator -v
git diff --check
```

Expected GREEN: all commands exit `0`.

- [ ] **Step 7: Commit**

```bash
git add scripts/harness_ai_infra_evidence.py scripts/tests/test_harness_ai_infra_evidence.py scripts/harness_loop_orchestrator.py docs/harness/planner-generator-evaluator-loop.md
git commit -m "feat(harness): validate ai infra gap proofs"
```

### Task 4: Required Evidence, Service Availability, And Freshness Gates

**Files:**
- Modify: `scripts/harness_ai_infra_evidence.py`
- Modify: `scripts/tests/test_harness_ai_infra_evidence.py`
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/tests/test_harness_loop_orchestrator.py`
- Modify: `docs/harness/planner-generator-evaluator-loop.md`

**Interfaces:**
- Produces: `validate_required_evidence_manifest(policy_required: Sequence[str], manifest: Mapping[str, Any], repo_root: Path, run_dir: Path) -> list[str]`
- Produces: `check_service_availability(services: Sequence[Mapping[str, str]], timeout_seconds: float = 2.0) -> dict[str, Any]`
- Produces artifact: `.codex/loop-runs/<run-id>/required-evidence-result.json`
- Consumes artifact: `.codex/loop-runs/<run-id>/required-evidence-manifest.json`

- [ ] **Step 1: Write failing required evidence manifest tests**

Add tests for a manifest shape:

```json
{
  "items": [
    {
      "evidence_id": "gap-proof",
      "status": "pass",
      "summary": "gap proof validated",
      "artifacts": [".codex/loop-runs/demo/gap-proofs/task.json"]
    }
  ]
}
```

The validator must require every policy `required_evidence` item to be represented by at least one manifest item using normalized keyword matching, require status `pass` or `blocked`, and require listed artifact files to exist inside repo or run dir.

Run: `python3 -m unittest scripts.tests.test_harness_ai_infra_evidence.HarnessAiInfraEvidenceTests.test_required_evidence_manifest_blocks_missing_items -v`

Expected RED: function missing.

- [ ] **Step 2: Write failing service helper tests**

Use a temporary `http.server` or mocked opener to verify `check_service_availability()` returns per-service `status`, `url`, `http_status`, and error text.

Run: `python3 -m unittest scripts.tests.test_harness_ai_infra_evidence.HarnessAiInfraEvidenceTests.test_check_service_availability_records_http_status -v`

Expected RED: function missing.

- [ ] **Step 3: Write failing orchestrator gate tests**

Add tests that:

- expanded policy with missing `required-evidence-manifest.json` blocks before commit
- manifest missing `service availability evidence` blocks before commit
- manifest with all required items and artifact files lets the commit proceed

Run: `python3 -m unittest scripts.tests.test_harness_loop_orchestrator.HarnessLoopOrchestratorTests.test_run_autonomous_blocks_expanded_policy_missing_required_evidence -v`

Expected RED: commit proceeds without manifest.

- [ ] **Step 4: Implement required evidence gate**

Before supply-chain and commit in `_commit_autonomous_changes()`, if `run["required_evidence"]` is non-empty:

1. Read `required-evidence-manifest.json`.
2. Validate it against `run["required_evidence"]`.
3. Also run the gap proof validator when required.
4. Write `required-evidence-result.json`.
5. Stop as `stopped_blocked` with `next_action="inspect_required_evidence"` if any finding exists.

- [ ] **Step 5: Implement service availability helper**

Use `urllib.request` from the Python standard library. The helper should not throw for connection failures; it returns a JSON-serializable result with `overall_status` equal to `pass` only when every service responds with HTTP `2xx` or `3xx`.

- [ ] **Step 6: Verify GREEN**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_ai_infra_evidence scripts.tests.test_harness_loop_orchestrator -v
git diff --check
```

Expected GREEN: all commands exit `0`.

- [ ] **Step 7: Commit**

```bash
git add scripts/harness_ai_infra_evidence.py scripts/tests/test_harness_ai_infra_evidence.py scripts/harness_loop_orchestrator.py docs/harness/planner-generator-evaluator-loop.md
git commit -m "feat(harness): gate autonomous runs on required evidence"
```

### Task 5: AI Infra Evaluator Scenario And Smoke

**Files:**
- Create: `scripts/harness_ai_infra_meta_loop_smoke.py`
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/tests/test_harness_loop_orchestrator.py`
- Create: `docs/harness/evaluator-scenarios/ai-infra-meta-loop-runtime-01.json`
- Modify: `docs/harness/planner-generator-evaluator-loop.md`

**Interfaces:**
- Produces CLI: `python3 scripts/harness_ai_infra_meta_loop_smoke.py --repo-root . --run-id evaluator-scenario-ai-infra-meta-loop-runtime --isolate-clone`
- Produces fake generator driver: `fake-expanded-code`
- Produces fake generator driver: `fake-missing-evidence`

- [ ] **Step 1: Write failing fake driver tests**

Add tests that `run_autonomous()` accepts `generator_driver="fake-expanded-code"` only when expanded policy is loaded. The driver writes one allowed `scripts/ai_infra_expanded_runtime_smoke.txt` path plus the required evidence manifest; the run should commit and return to planning.

Correction after hardening: the placeholder-only fake-expanded path is no longer expected to commit. When the smoke uses synthetic freshness placeholders instead of live pass evidence, the expected result is `overall_status=blocked`, `expanded_code_scope.status=blocked`, `synthetic_placeholder_block=true`, and no `commit-result.json`.

Add a paired test with `generator_driver="fake-missing-evidence"` that blocks with `inspect_required_evidence`.

Run: `python3 -m unittest scripts.tests.test_harness_loop_orchestrator.HarnessLoopOrchestratorTests.test_run_autonomous_expanded_policy_allows_code_path_with_evidence -v`

Expected RED: driver is unsupported.

- [ ] **Step 2: Implement fake expanded drivers**

Extend CLI choices and `_write_fake_autonomous_generator_result()`:

- `fake-expanded-code`: writes a harmless smoke text file under `scripts/`, writes valid gap proof, coverage map, and `required-evidence-manifest.json` artifacts covering every expanded policy required evidence label.
- `fake-missing-evidence`: writes the same code path but omits the manifest.

Keep the driver deterministic and local. Do not touch real service processes.

- [ ] **Step 3: Write failing smoke helper tests**

Add a test that calls the smoke helper in an isolated temporary clone and asserts the JSON output contains:

- `expanded_policy_preflight: pass`
- `expanded_code_scope: blocked`
- `missing_evidence_gate: pass`
- `service_availability_evidence: blocked`
- `synthetic_placeholder_block: true`

Run: `python3 -m unittest scripts.tests.test_harness_loop_orchestrator.HarnessLoopOrchestratorTests.test_ai_infra_meta_loop_smoke_helper_exercises_expanded_runtime -v`

Expected RED: smoke helper missing.

- [ ] **Step 4: Implement smoke helper**

The helper should:

1. Optionally clone the repo to a temporary directory with `--isolate-clone`.
2. Configure local git identity in the clone.
3. Run expanded autonomous preflight with `--policy-file docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json`.
4. Seed loop-state and coverage map with a candidate.
5. Run the missing-evidence driver and assert it blocks.
6. Reset to a clean committed state inside the clone.
7. Run the expanded-code driver and assert it commits.
8. Call `check_service_availability()` for the live project service URLs even when using `--isolate-clone`; if any service is unavailable, report blocked evidence instead of marking the smoke passed.
9. Print a compact JSON summary.

- [ ] **Step 5: Add evaluator scenario contract**

Create `docs/harness/evaluator-scenarios/ai-infra-meta-loop-runtime-01.json` with user scenarios covering E2E-3, E2E-5, and E2E-6 from the spec:

- expanded runtime gate
- code repair scope and denylist
- required evidence missing blocks
- service/dashboard/crawler freshness evidence exists

- [ ] **Step 6: Verify GREEN**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_orchestrator scripts.tests.test_harness_ai_infra_evidence -v
python3 scripts/harness_ai_infra_meta_loop_smoke.py --repo-root . --run-id evaluator-scenario-ai-infra-meta-loop-runtime --isolate-clone
python3 -m json.tool docs/harness/evaluator-scenarios/ai-infra-meta-loop-runtime-01.json >/dev/null
git diff --check
```

Expected GREEN: all commands exit `0`.

- [ ] **Step 7: Commit**

```bash
git add scripts/harness_ai_infra_meta_loop_smoke.py scripts/harness_loop_orchestrator.py scripts/tests/test_harness_loop_orchestrator.py docs/harness/evaluator-scenarios/ai-infra-meta-loop-runtime-01.json docs/harness/planner-generator-evaluator-loop.md
git commit -m "test(harness): add ai infra meta loop smoke"
```

### Task 6: Phase A To Phase B Meta Loop Transition

**Files:**
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/tests/test_harness_loop_orchestrator.py`
- Modify: `docs/harness/planner-generator-evaluator-loop.md`
- Modify: `tasks.json`
- Modify: `progress.md`

**Interfaces:**
- Produces: `transition_meta_loop_to_expansion(repo_root: Path | str, meta_run_id: str, expansion_run_id: str, policy_file: str, source_phase_commit: str, transition_evidence: Sequence[str]) -> dict[str, Any]`
- Produces CLI: `python3 scripts/harness_loop_orchestrator.py transition-meta --repo-root . --run-id <parent> --expansion-run-id <child> --policy-file <file> --source-phase-commit <sha> --transition-evidence <path>`
- Produces run fields: `phase_transition`, `transition_evidence`, `source_phase_commit`, `expansion_run_id`

- [ ] **Step 1: Write failing transition tests**

Add tests that a parent demand-development run in `passed_waiting_human_merge` with a real checkpoint commit and evidence files can transition to an autonomous expansion run.

Assertions:

```python
parent = load_run(repo_root, "ai-meta")
self.assertEqual(parent["phase"], "child_running")
self.assertEqual(parent["phase_transition"], "development_to_expansion")
self.assertEqual(parent["source_phase_commit"], checkpoint_sha)
self.assertEqual(parent["expansion_run_id"], "ai-meta-expansion")

expansion = load_run(repo_root, "ai-meta-expansion")
self.assertEqual(expansion["policy"], "autonomous_knowledge")
self.assertEqual(expansion["domain"], "ai_infra")
self.assertEqual(expansion["phase"], "planning")
self.assertEqual(expansion["policy_file"], "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json")
```

Run: `python3 -m unittest scripts.tests.test_harness_loop_orchestrator.HarnessLoopDemandMultiTaskTests.test_transition_meta_loop_to_expansion_creates_autonomous_child -v`

Expected RED: function missing.

- [ ] **Step 2: Write failing blocked transition tests**

Add tests that transition is refused when:

- parent is not passed
- checkpoint commit is missing
- transition evidence file is missing
- policy file is invalid
- expansion run id already exists

Run: `python3 -m unittest scripts.tests.test_harness_loop_orchestrator.HarnessLoopDemandMultiTaskTests.test_transition_meta_loop_blocks_without_checkpoint_evidence -v`

Expected RED: function missing.

- [ ] **Step 3: Implement transition helper and CLI**

Implement `transition_meta_loop_to_expansion()` by:

1. Loading and validating the parent run.
2. Checking parent phase is `passed_waiting_human_merge`.
3. Verifying `git cat-file -e <source_phase_commit>^{commit}` succeeds.
4. Verifying each transition evidence path exists and stays in repo or `.codex/loop-runs/<run-id>/`.
5. Creating a confirmed autonomous preflight child using the expanded policy file.
6. Updating the parent to `phase="child_running"` and `next_action="run_autonomous_planner"`.
7. Appending a loop event with actor `orchestrator` and event type `phase_transition`.

- [ ] **Step 4: Update task status and docs**

After verification passes, mark `ai-infra-meta-loop-runtime-01` as `done` in `tasks.json` and add a top `progress.md` entry with:

- commits created
- test commands
- smoke helper output path or JSON summary
- service health check results
- note that Phase B autonomous knowledge expansion can now start

- [ ] **Step 5: Final verification**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_autonomous scripts.tests.test_harness_loop_orchestrator scripts.tests.test_harness_ai_infra_evidence -v
python3 scripts/harness_ai_infra_meta_loop_smoke.py --repo-root . --run-id evaluator-scenario-ai-infra-meta-loop-runtime --isolate-clone
python3 -m json.tool tasks.json >/dev/null
python3 -m json.tool docs/harness/evaluator-scenarios/ai-infra-meta-loop-runtime-01.json >/dev/null
python3 - <<'PY'
from pathlib import Path
from scripts.harness_loop_contracts import read_json_file, validate_loop_policy_payload
for path in Path("docs/harness/loop-policies").glob("*.json"):
    validate_loop_policy_payload(read_json_file(path))
PY
curl --noproxy '*' -fsS http://127.0.0.1:8765/api/health
curl --noproxy '*' -fsSI http://127.0.0.1:5173/ | sed -n '1,5p'
curl --noproxy '*' -fsS http://127.0.0.1:8766/api/health
git diff --check
```

Expected GREEN: all commands exit `0`; service checks show crawler backend, crawler frontend, and Loop Dashboard are reachable.

- [ ] **Step 6: Commit**

```bash
git add scripts/harness_loop_orchestrator.py scripts/tests/test_harness_loop_orchestrator.py docs/harness/planner-generator-evaluator-loop.md tasks.json progress.md
git commit -m "feat(harness): transition ai infra meta loops to expansion"
```

## Self-Review

Spec coverage:
- Expanded policy runtime loading is Task 1.
- Coverage map state and no-action gate is Task 2.
- Gap proof and dedupe validation is Task 3.
- Required evidence, service availability, dashboard/crawler freshness gates are Task 4.
- AI infra evaluator smoke for E2E-3, E2E-5, and E2E-6 is Task 5.
- Phase A to Phase B transition and E2E-7 is Task 6.

Placeholder scan:
- No task uses TBD/TODO/later placeholders.
- Each task has concrete files, interfaces, RED/GREEN commands, and commit scope.

Type consistency:
- `policy_file`, `manual_confirm_paths`, `required_evidence`, `coverage-map.json`, `required-evidence-manifest.json`, and transition field names are consistent across tasks.
