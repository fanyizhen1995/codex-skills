# External Orchestrator Runbook

## Setup

```bash
python3 -m venv .venv-harness-evaluator
source .venv-harness-evaluator/bin/activate
pip install -r scripts/requirements-harness-evaluator.txt
```

## Dry-run

```bash
python3 scripts/harness_evaluator_orchestrator.py run-task-loop --driver fake --task-id harness-evaluator-gates-01 --max-attempts 2
```

`run-task-loop --driver fake` now models scenario-first semantics:

- missing scenario metadata => `blocked`
- executable user scenarios with a failing first attempt => `fail`
- repaired scenarios on a later attempt => `pass`

## Automatic Gate Dry-run

```bash
python3 scripts/harness_evaluator_orchestrator.py run-task-auto-gate --driver fake --task-id harness-evaluator-usage-simulation-01 --repo-root "$PWD" --max-attempts 3
```

`run-task-auto-gate --driver fake` consumes the stop-hook actions directly:

- no task bundle yet => hook auto-prepares attempt 1 and returns `action=run_task_evaluator`
- failed task result => hook auto-prepares the next attempt and returns `action=rerun_task_evaluator`
- passed task result => stop hook clears and the loop exits

## Live Codex CLI Auto Gate

```bash
python3 scripts/harness_evaluator_orchestrator.py run-task-auto-gate --driver codex-exec --task-id harness-evaluator-usage-simulation-01 --repo-root "$PWD" --max-attempts 3
```

`run-task-auto-gate --driver codex-exec` is the current practical automatic path:

- consumes hook decisions after the parent interactive Codex session has entered the Stop gate
- consumes `run_task_evaluator` / `rerun_task_evaluator`
- invokes `codex exec` in read-only mode against the prepared bundle
- records the returned JSON verdict into `result.json`
- updates session-state phase/attempt counters automatically
- continues into final gate when the task `eval_policy.final_level_required=true`
- sets `HARNESS_EVALUATOR_SKIP_HOOKS=1` for the read-only evaluator session so evaluator exit does not recursively trigger the same Stop hook path

This path depends on the local `codex` CLI being installed and authenticated.

## Legacy Codex SDK skeleton

```bash
python3 scripts/harness_evaluator_orchestrator.py run-task-loop --driver codex-sdk --task-id harness-evaluator-gates-01 --max-attempts 2
```

The SDK driver remains a skeleton and is not the recommended automatic path in this repo.
