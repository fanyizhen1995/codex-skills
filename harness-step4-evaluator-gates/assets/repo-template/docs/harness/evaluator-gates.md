# Evaluator Gates

## Bundle Layout

- `/.codex/evaluations/tasks/<task-id>/<timestamp>-attempt-<n>/`
- `/.codex/evaluations/finals/<bundle-id>/<timestamp>-attempt-<n>/`

Task-level evaluator bundles are the machine-readable evidence package for a single task. Final-level evaluator bundles are the machine-readable evidence package for a unified report or artifact bundle.

## Effective Policy Resolution

1. Start from `tasks.json.eval_defaults`.
2. Apply per-task `eval_policy` overrides when present.
3. If `requires_eval=false`, both task/final gates default to false unless explicitly overridden for a final bundle task.

The default compatibility profile for the first migration is `task_level_required=true`, `final_level_required=false`, `task_scope=code_and_local_k3s`, `final_scope=report_and_artifacts`, `max_task_eval_attempts=3`, and `max_final_eval_attempts=2`.

## Result Semantics

- `pass`: gate cleared
- `fail`: task gate hard-blocks; final gate soft-blocks
- `blocked`: evaluator could not reach a trustworthy verdict

`blocked` is not equivalent to `pass`. A blocked result must explain whether the root cause is missing evidence, unavailable environment, shared-resource lock conflict, or unresolved risk that prevents a trustworthy verdict.

For task-level evaluator runs, `fail` requires repair and re-evaluation before user manual acceptance can proceed. For final-level evaluator runs, `fail` still allows external reporting, but the report must be marked `not recommended for acceptance`.

## Scenario Metadata

- Task-level evaluator scenario metadata lives in `docs/harness/evaluator-scenarios/<task-id>.json`.
- `prepare-task` copies that metadata into `input.json` as `must_simulate`, `scenario_source`, and `user_scenarios`.
- If `must_simulate=true` and `user_scenarios=[]`, the task gate may only return `blocked`.
- The automatic task gate is entered from the parent interactive Codex session's `Stop` hook. The read-only evaluator itself may still run through `codex exec`.
- If a `requires_eval=true` task reaches the stop hook without a task bundle, the hook may auto-create the next task bundle and return `action=run_task_evaluator`.
- If the latest task-level result is `fail` or `blocked`, the hook may auto-create the next attempt bundle and return `action=rerun_task_evaluator`.
- If a task has `eval_policy.final_level_required=true` and task-level evaluation has passed, the hook may auto-create the next final bundle and return `action=run_final_evaluator`.
- If the latest final-level result is `fail` or `blocked`, the hook may auto-create the next final attempt and return `action=rerun_final_evaluator`.
- If `requires_eval=false`, the hook skips both gates unless an already-created bundle still needs contract enforcement.

## Task Result Contract

- Task-level `result.json` must always include `scenario_results`.
- A task-level `pass` is only valid when every required `scenario_id` has `status=pass` and non-empty evidence.
- `verify_commands`, logs, and reports are supporting evidence; they do not replace scenario execution.

## Session-State Fields

- `phase`
- `task_eval_attempt`
- `last_task_eval_result`
- `final_eval_attempt`
- `last_final_eval_result`
- `repair_from_eval`

These fields belong in the session-state evaluator block so the active session can record the current phase, attempt counters, last known task/final evaluator result, and whether the implementation is currently in a repair loop triggered by evaluator findings.
