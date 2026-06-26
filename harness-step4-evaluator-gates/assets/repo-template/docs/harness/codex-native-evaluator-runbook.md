# Codex-Native Evaluator Runbook

## Automatic Trigger

- The local `~/.codex/config.toml` Stop/SubagentStop hooks should call `python3 scripts/harness_evaluator_hook_driver.py stop` and `python3 scripts/harness_evaluator_hook_driver.py subagent-stop`.
- The developer-side auto-trigger entrypoint is an interactive Codex session ending. A standalone developer `codex exec` invocation does not currently fire the parent `Stop` hook.
- When a `requires_eval=true` task reaches the stop hook without an active task bundle, the hook now prepares the next task bundle automatically and returns a blocking decision with `action=run_task_evaluator`.
- When the latest task-level result is `fail` or `blocked`, the stop hook prepares the next attempt bundle and returns `action=rerun_task_evaluator`.
- When task evaluation passes and the task `eval_policy.final_level_required=true`, the stop hook now prepares a final bundle automatically and returns `action=run_final_evaluator`.
- If the latest final-level result is `fail` or `blocked`, the stop hook prepares the next final attempt and returns `action=rerun_final_evaluator`.
- Tasks with `requires_eval=false` are skipped entirely unless an older bundle already exists and still needs contract enforcement.
- If the platform cannot directly spawn a read-only evaluator subagent from the hook, use the returned `bundle_dir` with the commands below or use the `codex-exec` auto-gate driver from the external orchestrator runbook.
- The read-only evaluator path sets `HARNESS_EVALUATOR_SKIP_HOOKS=1` to avoid recursively re-entering Stop hooks when the evaluator `codex exec` session ends.

## Task-level

1. Author `docs/harness/evaluator-scenarios/<task-id>.json`.
2. `python3 scripts/harness_evaluator_cli.py prepare-task --repo-root "$PWD" --task-id <task-id> --attempt <n>`
3. In the active Codex session, send:
   `Spawn the task_evaluator subagent in read-only mode. Give it <bundle>/input.json. It must execute the bundle user_scenarios first, then use verify/artifacts as supporting evidence, and finally record a result with python3 scripts/harness_evaluator_cli.py record-result --bundle-dir <bundle>.`
4. If the subagent returns `fail`, fix findings and rerun step 2 with the next attempt number.
5. If the subagent returns `blocked`, fix missing scenario metadata or environment prerequisites before retrying.

## Final-level

1. `python3 scripts/harness_evaluator_cli.py prepare-final --repo-root "$PWD" --final-bundle-id <bundle-id> --attempt <n>`
2. In the active Codex session, send:
   `Spawn the final_evaluator subagent in read-only mode. Give it <bundle>/input.json. It must write result.json and summary.md.`
3. If the result is `fail`, include the output of `python3 scripts/harness_evaluator_cli.py render-final-banner --bundle-dir <bundle>` in the final report.
