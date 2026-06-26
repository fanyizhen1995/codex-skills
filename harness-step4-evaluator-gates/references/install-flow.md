# Install Flow

The target repo owns the runtime implementation. This skill installs or updates only:

- repo-side evaluator scripts, tests, docs, and bundle templates
- a generic demo task and scenario
- local `~/.codex/config.toml` Stop/SubagentStop hook wiring

Install order:

1. Verify the repo already has `AGENTS.md`, `docs/`, `tasks.json`, and `progress.md`.
2. Copy the Step4 repo template into the target repo.
3. Ensure the target repo contains a generic demo task and scenario.
4. Patch local Codex hooks to point at the repo-side `scripts/harness_evaluator_hook_driver.py`.
5. Run the live smoke from a clean evaluator-demo task state using a real interactive Codex session.

Notes:

- The Step4 runtime uses the repo-side hook driver to auto-consume `run_task_evaluator` / `rerun_task_evaluator` decisions and launch the read-only evaluator with `codex exec`.
- The developer-side trigger is the parent interactive Codex session ending. A standalone `codex exec` run does not currently fire `Stop` hooks.

Do not hard-code project-specific environment, testbed, product, or cluster information into the skill.
