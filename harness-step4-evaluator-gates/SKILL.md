---
name: harness-step4-evaluator-gates
description: Use when a project already has AGENTS.md, docs, tasks.json, and progress.md, and needs task/final evaluator gates installed, local Codex hooks wired, a demo task generated, and a live auto-trigger smoke run.
---

# Harness Step4 Evaluator Gates

Install evaluator-gate assets into an existing harness-enabled repo, wire local Stop/SubagentStop hooks, generate a demo task, and prove the evaluator auto-trigger works with a live interactive Codex smoke.

## Preconditions

- Target repo already has `AGENTS.md`, `docs/`, `tasks.json`, and `progress.md`
- Local `codex` CLI is installed and authenticated

## Workflow

1. Read `references/install-flow.md` before modifying the repo.
2. Run `scripts/install_step4.py --repo-root <repo>`.
3. Run `scripts/patch_codex_config.py --repo-root <repo>`.
4. Read `references/live-validation.md` before claiming success.
5. Run `scripts/run_live_smoke.py --repo-root <repo> --task-id harness-evaluator-demo-01`.
6. If the smoke passes, record the evidence in the target repo.

## Boundaries

- Keep runtime evaluator logic versioned in the target repo.
- Keep the skill project-agnostic; do not add project-specific cluster, product, or acceptance details.
- Treat local `~/.codex/config.toml` as user-local state; patch it idempotently and make the hook safe to no-op in repos without Step4 assets.
- The developer-side auto-trigger depends on an interactive Codex session ending; `codex exec` alone does not fire `Stop` hooks in the current CLI.
