# Live Validation

Success requires a real Stop hook path, not just unit tests.

Required proof:

1. A real interactive Codex session completes the demo task implementation and then exits.
   The live smoke may run that developer-side demo session with approvals/sandbox bypass enabled so the demo can write `.codex/evaluator-demo/...`; this is only for the validation harness, not for the evaluator itself.
2. The local Stop hook invokes the repo-side `scripts/harness_evaluator_hook_driver.py stop`.
3. The hook driver triggers a read-only evaluator via `codex exec`.
4. A new task bundle appears under `.codex/evaluations/tasks/<task-id>/...`.
5. That bundle contains `input.json`, `result.json`, and `summary.md`.
6. `result.json` reports `status=pass`, `gate=task`, and the expected `task_id`.
7. The live smoke captures a hook trace and interactive transcript under `.codex/tmp/`.

If the smoke fails, diagnose in this order:

1. Is the repo template installed?
2. Does `~/.codex/config.toml` contain Step4 Stop/SubagentStop hooks?
3. Does the target repo have a session-state entry for the demo task?
4. Did the interactive session actually run the demo producer and verify commands?
5. Did the Stop hook fire at all, according to the trace file?
6. Did the evaluator return invalid JSON or fail scenario execution?

Current CLI note:

- The current Codex CLI fires `Stop` / `SubagentStop` for interactive sessions.
- A standalone developer `codex exec` invocation is not sufficient to prove Stop-hook auto-trigger wiring.
