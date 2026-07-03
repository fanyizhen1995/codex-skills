# Loop Dashboard History Design

## Goal

Loop Dashboard must show completed loop runs that live in project worktrees, not only runs under the current checkout's `.codex/loop-runs`.

The immediate user-visible case is `loop-dashboard-dev`, whose evidence is under `.worktrees/loop-dashboard/.codex/loop-runs/loop-dashboard-dev`. When the dashboard is started from `/home/fyz/codex-skills`, that completed run should appear in the left run list and remain fully inspectable.

## Scope

Included:

- Read current project runs from `.codex/loop-runs`.
- Read project-local worktree runs from `.worktrees/*/.codex/loop-runs`.
- Deduplicate runs with the same `run_id` by keeping the newest `updated_at`.
- Expose each run's source path and source kind in API payloads.
- Show the run source in the frontend run detail.
- Validate through backend tests and the existing browser-click evaluator.

Excluded:

- Scanning global worktree directories outside the project.
- Cross-project monitoring.
- Writing or migrating historical loop artifacts.
- Adding edit/delete actions for loop history.

## Data Model

Each listed run keeps the existing payload shape and adds:

- `source_kind`: `current` or `worktree`.
- `source_path`: relative path to the run directory when it is under the project root.

`run_id` remains the URL identifier. When duplicated, the store keeps the run with the latest computed `updated_at`. This avoids adding route syntax for source selection in the first iteration.

## Read Boundaries

The backend remains read-only and only scans directories inside the configured `project_root`:

- `project_root/.codex/loop-runs`
- `project_root/.worktrees/*/.codex/loop-runs`

All artifact reads continue to use safe path checks. Worktree historical runs may reference project-level evaluator bundles; those reads still resolve against `project_root`.

## Frontend Behavior

The left list continues to show a single combined run list. Completed historical runs are selectable like active runs.

The detail header keeps the current summary cards and adds one `运行信息` row:

- `来源`: relative source path, such as `.worktrees/loop-dashboard/.codex/loop-runs/loop-dashboard-dev`

This keeps the layout readable and makes it clear why a completed historical run appears even when it is not in the current checkout's `.codex/loop-runs`.

## Acceptance Criteria

1. A run under `.worktrees/<name>/.codex/loop-runs/<run-id>/run.json` appears in `/api/runs`.
2. The same run is available through `/api/runs/<run-id>`, `/api/runs/<run-id>/events`, and `/api/runs/<run-id>/logs`.
3. Duplicate `run_id` entries prefer the latest `updated_at`.
4. Frontend run detail shows the source path.
5. Browser evaluator confirms a completed worktree history run is visible and selectable.
