# Planner Generator Evaluator Loop

Phase 1 wires the local loop orchestrator through the existing planner,
generator, and evaluator harnesses. It is intentionally narrow: fake drivers
exercise the durable state machine without calling Codex, while `codex-exec`
remains available for planner/generator prompts and evaluator auto-gate runs.
Phase 2 keeps the same demand-development policy and adds task-contract
evaluator input, scenario command evidence, artifact hygiene, cleanup, and an
explicit human merge gate after all automated checks finish.

## Scope

- `preflight` creates `.codex/loop-runs/<run-id>/run.json` and `preflight.md`.
  The run contract records the requirement, repeatable constraints, and stop
  conditions. Phase 1 defaults to `passed_waiting_human_merge`.
- `plan` writes `planner-output.json` and advances to `generating`.
- `generate` writes `generator-result.json` and advances to `evaluating`.
- `evaluate` calls `scripts/harness_evaluator_orchestrator.py`, copies the
  evaluator result into `evaluator-result.json`, and advances either to
  `passed_waiting_human_merge` or `repair_needed`.
- `run` executes the confirmed run from its current phase through evaluator
  completion.

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
After an evaluator pass, a non-empty artifact list moves the run to
`artifact_hygiene` with `next_action=run_artifact_hygiene`; an empty list still
moves directly to `passed_waiting_human_merge`.

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
traversal and binary or oversized artifacts, writes
`artifact-manifest.json`, and writes `redaction-manifest.json` when sensitive
text is redacted. A blocked hygiene result stops the run at `stopped_blocked`
for inspection; otherwise the run advances to `cleanup`.

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

The helper clears the previous smoke run and `.codex/tmp/phase-2-smoke-artifact.txt`,
runs fake planner/generator drivers, writes a non-empty generator artifact and
`task-contract.json` with a passing `scenario_commands` entry, then continues
`run_loop` from `evaluating`. A successful smoke reaches
`passed_waiting_human_merge` and leaves `scenario-command-results.json`,
`artifact-manifest.json`, and `cleanup-result.json` under the run directory.

## Human Merge Gate

Evaluator pass does not mean the loop is merged. A passing evaluator result
with no generator artifacts sets `phase` to `passed_waiting_human_merge`,
`last_result` to `pass`, and `next_action` to
`await_human_merge_confirmation`. A passing evaluator result with artifacts
must pass artifact hygiene and cleanup before reaching the same gate. A human
operator must inspect the run artifacts, decide whether to merge or continue
repairs, and perform any repository integration outside the loop.
