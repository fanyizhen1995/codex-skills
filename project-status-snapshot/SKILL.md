---
name: project-status-snapshot
description: Use when asked to inspect, recover, summarize, or continue a project's current state, task status, progress, blockers, recent work, performance progress, deployment readiness, or interrupted Codex history from a repository or server.
---

# Project Status Snapshot

## Purpose

Create an evidence-backed status snapshot for an active engineering project. Use local repository state and available Codex history before making claims.

## Evidence Order

Gather only what is needed for the user's scope, but prefer this order:

1. Current context: `pwd`, repo root, branch, `git status --short`, recent commits.
2. Project notes: `AGENTS.md`, `README*`, `docs/`, `plans/`, `reports/`, `bench*`, `sprint*`, active design or exec-plan files.
3. Work evidence: recent file mtimes, recent diffs, uncommitted changes, test/benchmark logs, deployment config.
4. Codex history when available: `~/.codex/session_index.jsonl`, `~/.codex/state_*.sqlite`, `~/.codex/shell_snapshots`, and relevant shell history.

Use `rg`/`rg --files` first. For SQLite, query narrow tables and fields instead of scanning large logs:

```bash
sqlite3 ~/.codex/state_5.sqlite \
  "SELECT title,cwd,tokens_used,datetime(updated_at,'unixepoch','localtime')
   FROM threads
   WHERE cwd LIKE '%/project-name%'
   ORDER BY updated_at DESC LIMIT 20;"
```

## Workflow

1. Identify the project and time window from the user request. If ambiguous, infer from cwd/open files and state that assumption.
2. Read project guidance before interpreting files.
3. Build a compact timeline of recent work from commits, modified files, docs, logs, and Codex thread titles.
4. Separate evidence from inference. Mark uncertain conclusions as likely, not fact.
5. If the user asks to continue work, end with the next concrete actions in priority order.

## Output Shape

Keep the report concise. Prefer these sections:

- `Current State`: what is true now, with branch/cwd and dirty files if relevant.
- `Recent Progress`: ordered bullets with dates or commit refs when available.
- `Blockers/Risks`: missing data, failing tests, unclear ownership, deployment risk, stale docs.
- `Next Actions`: 3-6 concrete steps, starting with the safest/highest-leverage step.
- `Evidence Checked`: short list of commands/files consulted.

Do not paste long logs or large file excerpts. Summarize and cite paths/commands.

## Heuristics For This User

- SCUDA/HAMI tasks usually need status across code, docs, benchmark results, and prior Codex threads.
- "当前任务状态", "梳理项目现状", "任务中断", "性能进展", "灰度/生产环境" all require a snapshot before proposing implementation.
- For performance work, include baseline/native/same-host/cross-host numbers only when backed by benchmark artifacts.
- For deployment work, include service status, config, recent errors, and rollback/gray status if accessible.
- For review-heavy workflows, distinguish top-level user threads from subagent review threads.

## Common Mistakes

- Do not answer from memory when repository or Codex history is available.
- Do not treat thread titles as proof of completion; cross-check files, commits, or logs.
- Do not run broad scans over multi-GB Codex logs unless a narrow query cannot answer the question.
- Do not modify files, restart services, or run long benchmarks unless the user explicitly asked to act after the snapshot.
