---
name: hami-gpu-flow-task-lifecycle
description: Use when claiming, designing, implementing, verifying, accepting, or merging HAMI GPU Flow PoC tasks, especially tasks.json/progress/sprint_output updates, worktree coordination, E2E evidence, user acceptance, or squash-to-poc work.
---

# HAMI GPU Flow Task Lifecycle

## Core Rule

Treat a GPU Flow task as a state machine. Do not mark `done`, squash, or merge until the task's verify/E2E evidence, evaluator requirement, and user acceptance are explicit.

## Workflow

1. Restore state: read `AGENTS.md`, `progress.md`, `tasks.json`, relevant `docs/design/*`, `docs/superpowers/specs/*`, `docs/superpowers/plans/*`, `git status --short --branch`, recent commits, and `.codex/session-state/*.json`.
2. Pick or confirm one independent task. Prefer existing `tasks.json` entries; if registering a new task, fill all fields and set `requires_eval` based on risk.
3. Claim it: create or update `.codex/session-state/<task-id>-<session>.json`; take `.codex/locks/*.json` only for shared resources such as local k3s, Helm release, Volcano config, or production gray.
4. Before implementation, write or update the design/plan and ask for confirmation when the user required pre-implementation approval.
5. Implement in an isolated worktree. Keep root `tasks.json`, `progress.md`, `sprint_output.md`, and `AGENTS.md` updates for the integration/coordination step unless explicitly authorized.
6. Verify using project scripts first: focused Go tests, `scripts/go-in-docker.sh make test`, license, tidy, import aliases, golangci-lint, build, Helm lint/package, Docker build/save, `git diff --check`, and task-specific E2E docs.
7. Record evidence paths in `sprint_output.md`; if `requires_eval=true`, wait for evaluator/user acceptance before setting `done`.
8. After acceptance, update `tasks.json`, prepend `progress.md`, squash or merge to `poc` only as requested, and include verification evidence in the final summary.

## Evidence Packet

Use concise Chinese:

- `任务`: id, branch/worktree, scope, non-scope.
- `改动`: code/docs/config touched.
- `验证`: command or experiment path, status, important failures/retries.
- `E2E`: local/gray/none and why.
- `验收`: evaluator/user acceptance state.
- `合入`: commit/squash status and remaining risks.

## Common Mistakes

- Do not mark `done` before user acceptance when project rules require manual acceptance.
- Do not run real k3s/Helm/Volcano/production operations without a lock and explicit target.
- Do not mix several GPU Flow tasks into one commit unless the user asked for a squash/integration pass.
- Do not treat `.codex/session-state` or `.codex/locks` as final evidence; final conclusions belong in `progress.md`, `sprint_output.md`, and task docs.
- Do not copy production-only Volcano/HAMi assumptions into local tests without confirming the target environment.
