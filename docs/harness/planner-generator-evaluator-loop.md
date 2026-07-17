# Planner Generator Evaluator Loop

Phase 1 wires the loop execution primitives through the existing planner,
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
- The Supervisor queues bounded Planner work, which writes `planner-output.json`
  and advances to `generating`.
- The Worker runs bounded Generator work, which writes `generator-result.json`
  and advances to `evaluating`.
- Demand-development Codex Evaluator work calls `scripts/harness_evaluator_orchestrator.py
  run-task-gate-once`, binds the task bundle to the current run and Generator
  attempt, copies the evaluator result into `evaluator-result.json`, and advances to
  `artifact_hygiene`, `passed_waiting_human_merge`, or `repair_needed`.
  This loop-only entrypoint runs or resumes one task gate bound to that Generator
  result and never consumes the final gate. The general `run-task-auto-gate`
  command retains its existing task-to-final behavior for non-loop workflows.
  Scenario command stdout/stderr evidence also forces `artifact_hygiene`,
  including failing scenario command paths, before the run is repairable.
- Bounded artifact hygiene scans declared generator artifacts and scenario command
  logs, then advances to `cleanup`, `repair_needed`, or `stopped_blocked`.
- Bounded cleanup removes retained temporary worktrees and advances to the human
  merge gate.
- Supervisor reconciliation advances a confirmed run one bounded action at a
  time through its registry-defined terminal or human-gate state.
- Demand-development parent planning emits `planner_decision` and
  `next_child_task`; each child writes its
  own `planner-output.json`, `task-contract.json`, `generator-result.json`,
  and `evaluator-result.json`; passed children use `phase=passed`, then the
  parent planner continues until the parent reaches
  `passed_waiting_human_merge`, `stopped_budget`, or `stopped_blocked`.

## Runtime Commands

```bash
python3 -m scripts.loop_supervisor.cli watch \
  --project-root /home/fyz/codex-skills

python3 -m scripts.loop_supervisor.cli worker \
  --project-root /home/fyz/codex-skills \
  --worker-id worker-01

python3 -m scripts.loop_supervisor.cli status \
  --project-root /home/fyz/codex-skills
```

The `codex-exec` parent planner must write a planner payload that satisfies
`validate_planner_output_payload` and includes the multi-task fields:
`planner_decision`, `next_child_task`, `backlog`, `blocked_reason`,
`done_criteria`, `reader_summary`, and `decision_required`. A passing child
does not wait for human merge by itself; the child returns `phase=passed` and
the parent records accepted changed paths before planning the next child.

### Supervisor And Worker

Supervisor is the only control-plane role. It discovers run artifacts, applies
the shared registry, and queues bounded actions. Worker leases and executes one
action at a time without owning transition policy. Detailed migration,
rollback, health, and retention procedures are in `docs/harness/loop-supervisor.md`.

Every real loop task must keep the following long-running processes online and
verify them before reporting progress:

- Crawler Workbench means both backend and frontend. Both must remain reachable
  at the configured remote-accessible ports, and reachability alone is not
  enough: the running backend/frontend versions must match the current intended
  worktree after code or configuration changes, and crawler data views must not
  be stale.
- After crawler ingest, source updates, search-index changes, or wiki/raw
  changes, verify crawler freshness through backend APIs and frontend views.
  The backend wiki/search/source APIs must reflect the latest committed or
  ingested data without relying on manual stale-index workarounds, and the
  frontend must show the same current data.
- Loop Dashboard remains reachable and points at the project root whose runs
  should be monitored.
- `loop-supervisor` remains running so service health, version freshness,
  user-decision escalation, Reviewer inputs, and continuation planning
  remain visible in one global panel.
- `loop-supervisor-worker` remains running so queued bounded actions execute.
- The loop run uses a stable run ID under `.codex/loop-runs` or a tracked
  worktree `.codex/loop-runs` directory so Loop Dashboard can display the
  active task, completed history, child tasks, audit results, and logs.

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

Hygiene and cleanup are Worker-only bounded actions selected by the registry;
operators do not invoke them directly.

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

The former Phase 2 multi-round smoke executable was retired at Supervisor
cutover. Its retained scenario contract now targets focused registry and
Worker tests; operators cannot execute Planner, Generator, Evaluator, hygiene,
or cleanup outside the Supervisor queue.

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
the current run directory. Relative artifact paths are checked against the run
directory first, then the repo root, so both `gap-proofs/<task-id>.json` and
`.codex/loop-runs/<run-id>/gap-proofs/<task-id>.json` are valid references for
run-local evidence. The gate writes
`.codex/loop-runs/<run-id>/required-evidence-result.json` before supply-chain
checks or commit and blocks the run with
`next_action=inspect_required_evidence` when findings exist.

Fresh generator and recovery artifacts must be bound to the current task. The
commit and recovery gates reject stale `generator-result.json`,
`required-evidence-manifest.json`, autonomous commit state, `commit-result.json`,
and `push-result.json` data when the artifact's `run_id` or `task_id` does not
match the active run. Dirty-path and required-evidence recovery may protect
unrelated local dirt only after the current generator result validates and its
declared artifact hashes still match the working tree.

Live semantic evidence for `service-availability`,
`crawler-workbench-freshness`, `loop-dashboard-freshness`,
`search-api-visibility`, and `frontend-visibility` must also carry trusted
provenance. The manifest item must reference the run-local
`trusted-live-evidence/<evidence-id>.json` artifact. During the required
evidence gate, the orchestrator generates or overwrites those artifacts from
live probes and records `run.json.trusted_live_evidence_state` as an
orchestrator-owned map from `evidence_id` to `artifact_path`, `sha256`,
`created_by: harness_loop_orchestrator`, and `captured_at`. The validator
requires the manifest path to resolve to the run-local trusted artifact and the
artifact bytes to match the sha256 recorded in run state. A manifest-level
`created_by` marker and a payload-level `created_by` marker are not trusted by
themselves, and generator-written pass artifacts without matching run state are
blocked before commit.

Expanded AI infra policies should use stable manifest `evidence_id` values
instead of copying the full prose requirement into `summary`. Current stable
IDs are:

- `confirmed-preflight`
- `policy-run-limits`
- `gap-proof`
- `coverage-map`
- `loop-state`
- `raw-evidence`
- `curated-wiki-source-refs`
- `wiki-validate`
- `search-api-visibility`
- `frontend-visibility`
- `crawler-workbench-freshness`
- `domain-channels`
- `loop-dashboard-freshness`
- `service-availability`
- `link-probe`
- `secret-scan`
- `code-tests`
- `autonomous-scope-result`
- `supply-chain-result`
- `commit-result`
- `no-action-evidence`

Legacy manifests remain compatible when they omit `evidence_id` and rely on a
summary-only fallback, but new tests and new manifest emitters should target
the stable IDs above. Use short summaries such as `confirmed preflight
captured`, `run.json records policy file and limits`, or `service checks
captured`; do not paste the policy requirement prose into `summary`.

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

```

The Worker uses the configured production drivers for real autonomous agent
execution. Supervisor still applies deterministic no-action checks from
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

The former Phase 3 and expanded AI infra multi-round smoke executables were
retired at Supervisor cutover. Their safety contracts remain covered by
bounded Worker, registry, required-evidence, scope, and service-evidence tests.
No evaluator scenario imports a private multi-round policy function.

When Phase A demand-development fixes finish and a reviewer has a checkpoint
commit to preserve, transition the parent meta loop into Phase B autonomous
expansion with:

```bash
python3 scripts/harness_loop_orchestrator.py transition-meta \
  --repo-root . \
  --run-id ai-infra-meta \
  --expansion-run-id ai-infra-meta-expansion \
  --policy-file docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json \
  --source-phase-commit <checkpoint-sha> \
  --transition-evidence docs/harness/planner-generator-evaluator-loop.md
```

The parent run must already be in `passed_waiting_human_merge`. The transition
verifies the checkpoint commit exists, refuses missing or out-of-repo evidence
paths, creates a confirmed `autonomous_knowledge` child run for `ai_infra` with
`run_kind=child` and `parent_run_id=<meta-run-id>`, and
updates the parent to `phase=child_running` with a `phase_transition` event in
`.codex/loop-runs/<run-id>/events.jsonl`. The parent `run.json` records
`phase_transition=development_to_expansion`, `source_phase_commit`,
`transition_evidence`, and `expansion_run_id` so the autonomous child can start
without losing the demand-development checkpoint context.

## Loop Dashboard

The local read-only Loop Dashboard lives under `apps/loop_dashboard/`. Start it
from a project checkout to monitor that current project by default:

```bash
python3 - <<'PY'
from pathlib import Path
import os
import secrets
import stat

path = Path(".codex/session-state/loop-dashboard/cursor-secret")
path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
path.parent.chmod(0o700)
try:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    pass
else:
    with os.fdopen(descriptor, "w", encoding="ascii") as stream:
        stream.write(secrets.token_urlsafe(48))
        stream.write("\n")
metadata = path.stat()
if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
    raise SystemExit(f"unsafe cursor secret file: {path}")
if len(path.read_text(encoding="ascii").strip().encode()) < 32:
    raise SystemExit(f"invalid cursor secret file: {path}")
PY
LOOP_DASHBOARD_CURSOR_SECRET="$(cat .codex/session-state/loop-dashboard/cursor-secret)" \
PYTHONPATH=apps/loop_dashboard/backend \
python3 -m uvicorn loop_dashboard.main:app --host 127.0.0.1 --port 8766
```

The cursor secret is stable uncommitted runtime state under the already ignored
`.codex/session-state/` tree. Reuse it across Dashboard restarts; do not commit
it or regenerate it for each launch.

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
LOOP_DASHBOARD_CURSOR_SECRET="$(cat .codex/session-state/loop-dashboard/cursor-secret)" \
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
LOOP_DASHBOARD_CURSOR_SECRET="$(cat .codex/session-state/loop-dashboard/cursor-secret)" \
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
