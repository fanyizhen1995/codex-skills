# Planner Generator Evaluator Loop

Phase 1 wires the local loop orchestrator through the existing planner,
generator, and evaluator harnesses. It is intentionally narrow: fake drivers
exercise the durable state machine without calling Codex, while `codex-exec`
remains available for planner/generator prompts and evaluator auto-gate runs.

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

## Human Merge Gate

Evaluator pass does not mean the loop is merged. A passing evaluator result
sets `phase` to `passed_waiting_human_merge`, `last_result` to `pass`, and
`next_action` to `await_human_merge_confirmation`. A human operator must inspect
the run artifacts, decide whether to merge or continue repairs, and perform any
repository integration outside Phase 1.
