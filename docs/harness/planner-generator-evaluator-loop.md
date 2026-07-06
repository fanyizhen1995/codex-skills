# Planner Generator Evaluator Loop

Phase 1 wires the local loop orchestrator through the existing planner,
generator, and evaluator harnesses. It is intentionally narrow: fake drivers
exercise the durable state machine without calling Codex, while `codex-exec`
remains available for planner/generator prompts and evaluator auto-gate runs.
Phase 2 keeps the same demand-development policy and adds task-contract
evaluator input, scenario command evidence, artifact hygiene, cleanup, and an
explicit human merge gate after all automated checks finish. Phase 3 adds the
`autonomous-knowledge` policy for bounded personal-wiki work: it plans from a
domain `loop-state.json`, auto-commits only allowlisted domain evidence, and
keeps planning until no-action, budget, or blocked stop conditions apply.

## Scope

- `preflight` creates `.codex/loop-runs/<run-id>/run.json` and `preflight.md`.
  The run contract records the requirement, repeatable constraints, and stop
  conditions. Phase 1 defaults to `passed_waiting_human_merge`.
  Autonomous preflights may also record `--policy-file` fixture data into
  `run.json`, including `allowed_paths`, `denylist_paths`,
  `manual_confirm_paths`, `required_evidence`, merged `limits`, and the
  fixture path itself. When no policy fixture is supplied, autonomous runtime
  scope falls back to the existing conservative defaults.
- `plan` writes `planner-output.json` and advances to `generating`.
- `generate` writes `generator-result.json` and advances to `evaluating`.
- `evaluate` calls `scripts/harness_evaluator_orchestrator.py`, copies the
  evaluator result into `evaluator-result.json`, and advances to
  `artifact_hygiene`, `passed_waiting_human_merge`, or `repair_needed`.
  Scenario command stdout/stderr evidence also forces `artifact_hygiene`,
  including failing scenario command paths, before the run is repairable.
- `artifact-hygiene` scans declared generator artifacts and scenario command
  logs, then advances to `cleanup`, `repair_needed`, or `stopped_blocked`.
- `cleanup` removes retained temporary worktrees and advances to the human
  merge gate.
- `run` executes the confirmed run from its current phase through evaluator,
  artifact hygiene, cleanup, and the human merge gate when applicable.
- `run-autonomous` executes the confirmed autonomous run from its current phase
  through planning, generation, evaluator pass, artifact hygiene, cleanup,
  auto-commit, and the next planning pass until it reaches `stopped_no_action`,
  `stopped_budget`, or `stopped_blocked`.
  It accepts fake drivers for smoke tests and `codex-exec` drivers for real
  planner, generator, and evaluator agent calls.

## Commands

```bash
python3 scripts/harness_loop_orchestrator.py preflight \
  --repo-root . \
  --mode demand-development \
  --requirement "Phase 1 full smoke" \
  --run-id smoke-phase-1 \
  --constraint "Keep changes scoped to harness loop files" \
  --stop-condition passed_waiting_human_merge \
  --confirm

python3 scripts/harness_loop_orchestrator.py run \
  --repo-root . \
  --run-id smoke-phase-1 \
  --planner-driver fake \
  --generator-driver fake \
  --evaluator-driver fake \
  --max-eval-attempts 2

python3 scripts/harness_loop_orchestrator.py status \
  --repo-root . \
  --run-id smoke-phase-1
```

For expanded autonomous knowledge runs, point `preflight` at a repo-relative
policy fixture. The fixture must stay inside the repository, be JSON, and
declare the same policy as `--mode`:

```bash
python3 scripts/harness_loop_orchestrator.py preflight \
  --repo-root . \
  --mode autonomous-knowledge \
  --requirement "Expand ai_infra" \
  --run-id ai-infra-expanded \
  --domain ai_infra \
  --policy-file docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json \
  --confirm
```

Fake evaluator runs require scenario metadata at
`docs/harness/evaluator-scenarios/<task-id>.json`. The fake planner derives
`task_id` as `<run-id>-task` when preflight did not provide one, and carries
run-level `allowed_paths`, `denylist_paths`, and `stop_conditions` into
`planner-output.json`.

## Phase 2 Commands

Task contracts can drive evaluator bundle input without requiring a registered
task lookup. Use `prepare-task --task-contract` when the loop has written or
received a temporary `task-contract.json`:

```bash
python3 scripts/harness_evaluator_cli.py prepare-task \
  --repo-root . \
  --task-id ignored-when-contract-has-task-id \
  --attempt 1 \
  --task-contract .codex/loop-runs/<run-id>/task-contract.json
```

When `task-contract.json` includes `scenario_commands`, `evaluate` runs those
commands from `repo_root` before invoking the evaluator. Their stdout, stderr,
exit code, and manifest are written under the loop run directory:

```text
.codex/loop-runs/<run-id>/scenario-commands/
.codex/loop-runs/<run-id>/scenario-command-results.json
```

Generator artifacts are listed in `generator-result.json` under `artifacts`.
After an evaluator pass, a non-empty artifact list or any scenario command
stdout/stderr logs move the run to `artifact_hygiene` with
`next_action=run_artifact_hygiene`. An empty generator artifact list moves
directly to `passed_waiting_human_merge` only when there are no scenario
command logs. Failed scenario commands still write evidence and enter
`artifact_hygiene`; after hygiene passes, the run returns to `repair_needed`.

Run hygiene and cleanup directly when operating the loop one step at a time:

```bash
python3 scripts/harness_loop_orchestrator.py artifact-hygiene \
  --repo-root . \
  --run-id <run-id>

python3 scripts/harness_loop_orchestrator.py cleanup \
  --repo-root . \
  --run-id <run-id>
```

`artifact-hygiene` scans only repo-relative artifact paths, rejects path
traversal and binary or oversized artifacts, includes scenario command
stdout/stderr logs from `scenario-command-results.json`, writes
`artifact-manifest.json`, and writes `redaction-manifest.json` when sensitive
text is redacted. A blocked hygiene result stops the run at `stopped_blocked`
for inspection; otherwise the run advances to `cleanup` for passing evaluator
paths or back to `repair_needed` for failing scenario command paths.

`cleanup` removes only retained paths recorded under the repository
`.worktrees/` directory and records `cleanup-result.json`. It does not remove
loop evidence under `.codex/loop-runs/<run-id>`.

The Phase 2 evaluator scenario uses a self-contained smoke helper instead of
the bare `preflight && run` flow:

```bash
python3 scripts/harness_loop_phase2_smoke.py \
  --repo-root . \
  --run-id evaluator-scenario-phase-2 \
  --task-id planner-generator-evaluator-loop-phase-2-01
```

The helper clears the previous smoke run,
`.codex/tmp/phase-2-smoke-artifact.txt`, and prior fake evaluator attempts for
the Phase 2 task id, then runs fake planner/generator drivers, writes a
non-empty generator artifact and `task-contract.json` with a passing
`scenario_commands` entry, then continues `run_loop` from `evaluating`. A
successful smoke reaches `passed_waiting_human_merge` and leaves
`scenario-command-results.json`, `artifact-manifest.json`, and
`cleanup-result.json` under the run directory; the fresh fake evaluator attempt
remains under `.codex/evaluations/tasks/<task-id>/`.

## Phase 3 Commands

Policy fixtures live under `docs/harness/loop-policies/` and validate with
`scripts.harness_loop_contracts.validate_loop_policy_payload`:

```bash
python3 - <<'PY'
from pathlib import Path
from scripts.harness_loop_contracts import read_json_file, validate_loop_policy_payload
for path in Path("docs/harness/loop-policies").glob("*.json"):
    validate_loop_policy_payload(read_json_file(path))
PY
```

`docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json` is
an AI infrastructure expansion policy fixture. It records the stricter
preflight/evaluator contract for repo-wide autonomous repair during
`ai_infra` knowledge expansion: gap proofs, duplicate checks, search/frontend
visibility, link probes, secret scans, and code tests when crawler, harness,
frontend, or backend files change. The runtime now enforces the fixture's
`required_evidence` list at the autonomous commit gate through
`.codex/loop-runs/<run-id>/required-evidence-manifest.json`, while unchanged
scope defaults still come from the existing conservative
`autonomous-knowledge` runtime helpers.

When an autonomous run carries any policy `required_evidence`, the commit gate
requires `.codex/loop-runs/<run-id>/required-evidence-manifest.json` with an
`items` list (legacy `evidence` still reads for older artifacts). Each required
policy line must be represented by a matching manifest item with `status:
pass|blocked` and at least one artifact path that resolves inside the repo or
the current run directory. The gate writes
`.codex/loop-runs/<run-id>/required-evidence-result.json` before supply-chain
checks or commit and blocks the run with
`next_action=inspect_required_evidence` when findings exist.

When a required evidence policy line mentions `gap proof`, the same commit gate
also writes `.codex/loop-runs/<run-id>/gap-proof-result.json` and re-validates
the referenced payload for the current task. Direct gap-proof files under
`.codex/loop-runs/<run-id>/gap-proofs/<task-id>.json` remain valid artifacts,
but they no longer bypass the required manifest.

Service health evidence can be generated with
`scripts.harness_ai_infra_evidence.check_service_availability()`, which records
per-service status, URL, HTTP status, and error text without raising on
connection failures.

Start an autonomous run with an explicit domain and confirmed preflight:

```bash
python3 scripts/harness_loop_orchestrator.py preflight \
  --repo-root . \
  --mode autonomous-knowledge \
  --requirement "Expand ai_infra wiki coverage" \
  --run-id autonomous-ai-infra-smoke \
  --domain ai_infra \
  --constraint "Only auto-commit allowlisted personal-wiki domain artifacts" \
  --stop-condition stopped_no_action \
  --stop-condition stopped_budget \
  --stop-condition stopped_blocked \
  --confirm

python3 scripts/harness_loop_orchestrator.py run-autonomous \
  --repo-root . \
  --run-id autonomous-ai-infra-smoke \
  --planner-driver fake \
  --generator-driver fake \
  --evaluator-driver fake \
  --max-eval-attempts 2 \
  --max-tasks 2
```

Use `--planner-driver codex-exec --generator-driver codex-exec
--evaluator-driver codex-exec` for real autonomous agent execution. The
orchestrator still applies deterministic no-action checks from
`loop-state.json`, attempt limits, artifact hygiene, scope checks, supply-chain
checks, wiki validation, and commit safety gates around those agent calls.

The domain state file is
`personal-wiki/domains/<domain>/loop-state.json`. No-action requires an empty
`candidate_backlog`, empty `coverage_gaps`, at least one `known_sources` item,
fresh `last_scan_at` within `scan_ttl_days`, and non-empty
`no_action_evidence`.

For `ai_infra`, no-action also requires a valid coverage file at
`personal-wiki/domains/ai_infra/coverage-map.json`. The map must contain all
eight coverage layers:

- `training-distributed`
- `inference-runtime`
- `orchestration-scheduling`
- `data-rag-vector`
- `eval-observability-reliability`
- `security-governance-cost`
- `hardware-accelerator`
- `network-storage-cluster`

Each layer records `status`, `covered_pages`, `raw_evidence`,
`candidate_gaps`, `blocked_reason`, `last_scanned_at`, and `notes`. Missing or
invalid coverage maps stop the run at `stopped_blocked` with
`next_action=inspect_ai_infra_coverage_map` and write
`.codex/loop-runs/<run-id>/coverage-map-result.json`. Even with a valid file,
no-action is denied if any layer still has `candidate_gaps`, any layer scan is
stale, or `no_action_evidence` does not reference `coverage-map`.

Autonomous commits are restricted to personal-wiki domain wiki/raw/source and
manifest paths plus that domain's `loop-state.json` and `coverage-map.json`.
Changes under
`tasks.json`, `progress.md`, `docs/**`, or `scripts/**` require manual
confirmation and stop the run. Denylist paths such as `.env`, secrets, tokens,
or credential paths always stop the run. Dependency files require supply-chain
necessity and verification evidence before commit. The loop never auto-merges
main. If any path the generator wants to commit was already dirty during
preflight, the loop stops at `stopped_blocked` instead of committing pre-existing
user work. Generator agent failures are retried up to
`max_generator_attempts_per_task`; exhausting the limit stops the run for
inspection.

The Phase 3 evaluator scenario uses a self-contained smoke helper:

```bash
python3 scripts/harness_loop_phase3_smoke.py \
  --repo-root . \
  --run-id evaluator-scenario-phase-3 \
  --domain ai_infra \
  --task-id planner-generator-evaluator-loop-phase-3-01 \
  --isolate-clone
```

With `--isolate-clone`, the helper clones the current checkout into a temporary
directory, configures git identity only inside that clone, and discards the
clone after the smoke finishes. Inside the smoke repo it clears the previous
smoke run and prior generated autonomous raw notes for the same run id, creates
confirmed autonomous preflight against a clean smoke baseline, seeds
`loop-state.json` with one candidate backlog item and one known source, and runs
fake autonomous drivers with
`max_tasks=2`. A successful smoke proves the first pass created a git commit for
allowlisted wiki evidence and loop state, then the second planner pass stopped
at `stopped_no_action`. It prints JSON containing `phase`, `next_action`,
`commit`, `loop_state_path`, and run artifact paths. Running without
`--isolate-clone` is intended only for disposable clones; the helper refuses to
overwrite dirty smoke loop-state or generated raw paths.

## Loop Dashboard

The local read-only Loop Dashboard lives under `apps/loop_dashboard/`. Start it
from a project checkout to monitor that current project by default:

```bash
PYTHONPATH=apps/loop_dashboard/backend \
python3 -m uvicorn loop_dashboard.main:app --host 127.0.0.1 --port 8766
```

Open `http://127.0.0.1:8766`. The frontend is Chinese and polls the backend for
loop runs, agent summaries, flow state, events, logs, completed states, and
blocked diagnostics. The backend only reads loop/evaluator artifacts from the
configured project root; it does not execute, delete, restart, merge, or roll
back loop runs.

The dashboard has no authentication layer. Keep the default `127.0.0.1`
binding unless the port is exposed through a trusted tunnel or controlled
network.

For long-running remote monitoring in this project, keep the dashboard online
in a named tmux session and bind only on a trusted network:

```bash
tmux new -s loop-dashboard
cd /home/fyz/codex-skills
PYTHONPATH=apps/loop_dashboard/backend \
python3 -m uvicorn loop_dashboard.main:app --host 0.0.0.0 --port 8766
```

During AI infrastructure autonomous expansion runs, the operator must keep
Crawler Workbench backend `8765`, Crawler Workbench frontend `5173`, and Loop
Dashboard `8766` available so the user can continuously inspect state. If a
service is restarted, record the reason and verify:

```bash
curl --noproxy '*' http://127.0.0.1:8765/api/health
curl --noproxy '*' -I http://127.0.0.1:5173/
curl --noproxy '*' http://127.0.0.1:8766/api/health
```

To inspect a different project, point `LOOP_DASHBOARD_PROJECT_ROOT` at that
checkout:

```bash
PYTHONPATH=apps/loop_dashboard/backend \
LOOP_DASHBOARD_PROJECT_ROOT=/path/to/other/project \
python3 -m uvicorn loop_dashboard.main:app --host 127.0.0.1 --port 8766
```

Browser-click evaluator:

```bash
python3 scripts/loop_dashboard_evaluator.py \
  --repo-root . \
  --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01
```

The evaluator starts the dashboard against a temporary fixture project, opens
the page with Playwright, clicks through run selection, agent cards, flow state,
log filtering, redaction, and completed states, then writes the result bundle
under the requested output directory.

## Human Merge Gate

Evaluator pass does not mean the loop is merged. A passing evaluator result
with no generator artifacts sets `phase` to `passed_waiting_human_merge`,
`last_result` to `pass`, and `next_action` to
`await_human_merge_confirmation` only when no scenario command logs were
produced. A passing evaluator result with artifacts or scenario command logs
must pass artifact hygiene and cleanup before reaching the same gate. A human
operator must inspect the run artifacts, decide whether to merge or continue
repairs, and perform any repository integration outside the loop.
