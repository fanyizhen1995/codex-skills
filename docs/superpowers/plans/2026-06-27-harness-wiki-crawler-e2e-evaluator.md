# Harness Wiki Crawler E2E Evaluator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install harness steps 1-4 in this repository and add an end-to-end evaluator scenario that independently validates the Personal Wiki Crawler Workbench.

**Architecture:** Root harness files provide durable project context and session state. Step4 installs generic evaluator runtime under `scripts/`, `docs/harness/`, and `.codex/evaluations/templates/`. A crawler-specific evaluator helper and scenario execute the workbench workflow in an isolated state directory and record machine-readable evidence for the task gate.

**Tech Stack:** Bash, Python 3, FastAPI TestClient, SQLite, Codex CLI, existing `personal-wiki` CLI, Step4 evaluator runtime.

---

## File Structure

- Create `AGENTS.md`: root agent guide and harness workflow map.
- Create `docs/ARCHITECTURE.md`: repository module map and crawler workbench data flow.
- Create `docs/CONVENTIONS.md`: observed file, code, test, and commit conventions.
- Create `docs/TECH_DECISIONS.md`: inferred technology decisions with explicit unknowns.
- Create `docs/QUALITY.md`: local definition of done and validation commands.
- Create `docs/exec-plans/active/.gitkeep`, `docs/exec-plans/completed/.gitkeep`, `docs/exec-plans/backlog.md`, `docs/exec-plans/tech-debt-tracker.md`: harness step 1/2 planning knowledge base.
- Create `init.sh`: quick session bootstrap and validation script.
- Create `tasks.json`: task state with evaluator defaults and crawler evaluator task.
- Create `progress.md`: human-readable session state.
- Use `harness-step4-evaluator-gates/scripts/install_step4.py`: copy generic Step4 runtime into the repo and add the Step4 demo task.
- Use `harness-step4-evaluator-gates/scripts/patch_codex_config.py`: patch local Codex hooks idempotently.
- Create `scripts/wiki_crawler_e2e_evaluator.py`: executable scenario helper that drives crawler workbench services directly and emits evidence.
- Create `docs/harness/evaluator-scenarios/wiki-crawler-e2e-eval-01.json`: Step4 scenario contract for the crawler task.
- Modify `tasks.json`: add `wiki-crawler-e2e-eval-01` after Step4 installer appends its demo task.
- Modify `progress.md`: append installation and verification evidence.

## Task 1: Install Harness Step 1/2 Docs

**Files:**
- Create: `AGENTS.md`
- Create: `docs/ARCHITECTURE.md`
- Create: `docs/CONVENTIONS.md`
- Create: `docs/TECH_DECISIONS.md`
- Create: `docs/QUALITY.md`
- Create: `docs/exec-plans/active/.gitkeep`
- Create: `docs/exec-plans/completed/.gitkeep`
- Create: `docs/exec-plans/backlog.md`
- Create: `docs/exec-plans/tech-debt-tracker.md`

- [ ] **Step 1: Write root harness docs**

Create the root files with repository-specific content based on `README.md`, `personal-wiki/apps/crawler_workbench/README.md`, the Python/TypeScript source tree, and the committed design/spec files. Keep `AGENTS.md` under 150 lines and include concrete commands:

```bash
bash init.sh
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q
cd personal-wiki/apps/crawler_workbench/frontend && npm test && npm run build
```

- [ ] **Step 2: Validate docs links and content**

Run:

```bash
test -f AGENTS.md
test -f docs/ARCHITECTURE.md
test -f docs/CONVENTIONS.md
test -f docs/TECH_DECISIONS.md
test -f docs/QUALITY.md
test -f docs/exec-plans/backlog.md
test -f docs/exec-plans/tech-debt-tracker.md
wc -l AGENTS.md
```

Expected: every file exists and `AGENTS.md` is under 150 lines.

## Task 2: Install Harness Step 3 Session State

**Files:**
- Create: `init.sh`
- Create: `tasks.json`
- Create: `progress.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Create `init.sh`**

Write a quick environment script that checks repository location, validates `tasks.json` when present, validates the wiki, and prints optional backend/frontend test commands without installing dependencies automatically.

- [ ] **Step 2: Create initial `tasks.json`**

Create JSON with:

```json
{
  "project": "codex-skills",
  "last_updated": "2026-06-27",
  "current_focus": "Install harness evaluator gates and validate the personal wiki crawler end-to-end.",
  "eval_defaults": {
    "task_level_required": true,
    "final_level_required": false,
    "task_scope": "local_repo_and_personal_wiki",
    "final_scope": "report_and_artifacts",
    "max_task_eval_attempts": 3,
    "max_final_eval_attempts": 2
  },
  "tasks": [
    {
      "id": "wiki-crawler-e2e-eval-01",
      "title": "Validate wiki crawler end-to-end through independent evaluator",
      "description": "Run a dedicated evaluator scenario that exercises crawler fetch, queue approval, ingest, index, backlinks, and validation from a user perspective.",
      "status": "pending",
      "priority": "high",
      "blocked_by": "",
      "verify": "python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/wiki-crawler-e2e-eval-01",
      "requires_eval": true,
      "eval_policy": {
        "task_level_required": true,
        "final_level_required": false,
        "task_scope": "local_repo_and_personal_wiki",
        "final_scope": "report_and_artifacts",
        "max_task_eval_attempts": 3,
        "max_final_eval_attempts": 2
      }
    }
  ]
}
```

- [ ] **Step 3: Create `progress.md`**

Add an initial top entry for harness initialization and record that the crawler E2E evaluator task is the current focus.

- [ ] **Step 4: Validate Step 3 files**

Run:

```bash
bash init.sh
python3 -m json.tool tasks.json > /dev/null
head -30 progress.md
```

Expected: commands exit 0 and progress has a harness initialization entry.

## Task 3: Install Step4 Runtime And Hooks

**Files:**
- Create/Modify via installer: `scripts/harness_evaluator_*.py`
- Create/Modify via installer: `scripts/requirements-harness-evaluator.txt`
- Create/Modify via installer: `docs/harness/**`
- Create/Modify via installer: `.codex/evaluations/templates/**`
- Modify via installer: `tasks.json`
- Modify local user config: `~/.codex/config.toml`

- [ ] **Step 1: Run Step4 installer**

Run:

```bash
python3 harness-step4-evaluator-gates/scripts/install_step4.py --repo-root .
```

Expected: prints `{"status": "ok", ...}` and appends or updates `harness-evaluator-demo-01` in `tasks.json`.

- [ ] **Step 2: Patch Codex hook config**

Run:

```bash
python3 harness-step4-evaluator-gates/scripts/patch_codex_config.py --repo-root .
```

Expected: local `~/.codex/config.toml` contains safe no-op Step4 Stop/SubagentStop hook commands.

- [ ] **Step 3: Validate Step4 runtime tests**

Run:

```bash
python3 harness-step4-evaluator-gates/scripts/test_step4_skill.py
```

Expected: unit tests pass.

## Task 4: Add Wiki Crawler E2E Evaluator Helper

**Files:**
- Create: `scripts/wiki_crawler_e2e_evaluator.py`
- Create: `docs/harness/evaluator-scenarios/wiki-crawler-e2e-eval-01.json`
- Modify: `tasks.json`

- [ ] **Step 1: Write helper script**

Create `scripts/wiki_crawler_e2e_evaluator.py` with a `--repo-root` and `--output-dir` CLI. The script should:

```text
1. Resolve repo root and backend package path.
2. Use `.codex/wiki-crawler-e2e/state` as isolated workbench state.
3. Write a deterministic `sources.yaml` with a small RSS or web source for `ai_infra`.
4. Initialize the FastAPI app with scheduler disabled.
5. Run the source once through `run_source_once`.
6. Approve the first generated queue task.
7. Run the approved task with a local fake Codex runner that writes a small curated draft tied to the raw source.
8. Run index, backlinks, domain validate, and full validate.
9. Write `result.json`, `summary.md`, and command logs into `--output-dir`.
10. Exit 0 only when all required evidence exists.
```

The fake Codex runner is allowed only inside this evaluator helper so the scenario verifies the workbench orchestration path without requiring the evaluator to mutate arbitrary content through a real model.

- [ ] **Step 2: Write scenario contract**

Create `docs/harness/evaluator-scenarios/wiki-crawler-e2e-eval-01.json`:

```json
{
  "task_id": "wiki-crawler-e2e-eval-01",
  "must_simulate": true,
  "user_scenarios": [
    {
      "scenario_id": "wiki-crawler-e2e-user-flow",
      "user_goal": "As a wiki crawler user, prove that a trusted source can be fetched, approved, ingested, indexed, linked, and validated with durable evidence.",
      "prerequisites": [
        "Harness Step4 runtime is installed.",
        "personal-wiki ai_infra domain exists.",
        "Local Python dependencies for crawler_workbench are available."
      ],
      "entrypoint": "python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/wiki-crawler-e2e-eval-01",
      "steps": [
        "Run the evaluator helper entrypoint.",
        "Inspect result.json and summary.md in the output directory.",
        "Confirm domain and full wiki validation succeeded."
      ],
      "expected_outcomes": [
        "At least one raw crawler evidence file is written.",
        "The ingest task reaches succeeded.",
        "Index and backlinks are rebuilt.",
        "Domain and full wiki validation return zero issues.",
        "The output result.json reports status pass with evidence paths."
      ],
      "failure_signals": [
        "No raw evidence file is created.",
        "The queue never contains an approvable task.",
        "The ingest task fails or remains pending.",
        "Wiki validation reports issues.",
        "The output directory lacks result.json or summary.md."
      ],
      "cleanup": [
        "Remove .codex/wiki-crawler-e2e/ if a clean rerun is needed."
      ],
      "automation_hint": "shell"
    }
  ]
}
```

- [ ] **Step 3: Ensure task entry survives Step4 installer**

After Step4 installer updates `tasks.json`, confirm both task IDs exist:

```bash
python3 - <<'PY'
import json
payload = json.load(open("tasks.json", encoding="utf-8"))
ids = {task["id"] for task in payload["tasks"]}
assert "harness-evaluator-demo-01" in ids
assert "wiki-crawler-e2e-eval-01" in ids
PY
```

Expected: command exits 0.

## Task 5: Verify Harness And Evaluator

**Files:**
- Modify: `progress.md`

- [ ] **Step 1: Run local validation**

Run:

```bash
bash init.sh
python3 -m json.tool tasks.json > /dev/null
python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/wiki-crawler-e2e-eval-01
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate
git diff --check
```

Expected: commands pass, or any blocker is recorded with exact output.

- [ ] **Step 2: Run Step4 live smoke**

Run:

```bash
python3 harness-step4-evaluator-gates/scripts/run_live_smoke.py --repo-root . --task-id harness-evaluator-demo-01
```

Expected: a new pass result for `harness-evaluator-demo-01` appears under `.codex/evaluations/tasks/`.

- [ ] **Step 3: Run crawler task gate through Step4 CLI path**

Run:

```bash
python3 scripts/harness_evaluator_cli.py prepare-task --repo-root . --task-id wiki-crawler-e2e-eval-01
python3 scripts/harness_evaluator_orchestrator.py run-task-auto-gate --driver fake --task-id wiki-crawler-e2e-eval-01 --repo-root . --max-attempts 1
```

Expected: a task bundle exists for `wiki-crawler-e2e-eval-01`. If the fake driver only proves bundle wiring, the helper output from Step 1 remains the scenario evidence.

- [ ] **Step 4: Record evidence**

Append to `progress.md`:

```markdown
## 2026-06-27 Harness Step4 Wiki Crawler E2E

- Installed harness steps 1-3.
- Installed Step4 evaluator gates and local hooks.
- Added `wiki-crawler-e2e-eval-01`.
- Evidence:
  - `.codex/wiki-crawler-e2e/wiki-crawler-e2e-eval-01/result.json`
  - `.codex/evaluations/tasks/harness-evaluator-demo-01/`
  - `.codex/evaluations/tasks/wiki-crawler-e2e-eval-01/`
- Verification notes: <record exact pass/blocker details from this run>
```

- [ ] **Step 5: Commit only owned harness files**

Run:

```bash
git status --short
git add AGENTS.md docs init.sh tasks.json progress.md scripts/harness_evaluator_*.py scripts/requirements-harness-evaluator.txt scripts/wiki_crawler_e2e_evaluator.py .codex/evaluations/templates
git commit -m "feat(harness): add wiki crawler evaluator gates"
```

Expected: unrelated pre-existing files remain uncommitted.

