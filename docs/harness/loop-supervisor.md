# Loop Supervisor Operations

## Runtime roles

The Loop Supervisor is the only public loop control role. It reconciles run
artifacts, owns transition policy and Reviewer scheduling, and queues bounded
actions in `.codex/supervisor/supervisor.db`. A Worker leases and executes those
actions. The Reviewer is a short-lived read-only subprocess, not a long-running
service.

There are exactly two long-running loop runtime commands. Run each in its own
tmux session from the repository root:

```bash
python3 -m scripts.loop_supervisor.cli watch --project-root /home/fyz/codex-skills
python3 -m scripts.loop_supervisor.cli worker --project-root /home/fyz/codex-skills --worker-id worker-01
```

The legacy auto-resume watcher is removed. The legacy multi-round execution and
Auditor commands are not public commands. Low-level phase primitives remain
internal Worker implementation details.

Task 9 installs and validates this runtime but does not cut over the live
services. The old runtime remains the executor until the Task 10 gates pass.

## Status and health

```bash
python3 -m scripts.loop_supervisor.cli status --project-root /home/fyz/codex-skills
python3 -m scripts.loop_supervisor.cli health --project-root /home/fyz/codex-skills
curl --noproxy '*' http://127.0.0.1:8766/api/health
```

`status` reports SQLite record counts and Worker heartbeats. `health` verifies
database integrity, WAL mode, and foreign-key enforcement. The Dashboard is
read-only and remains separately available at `http://127.0.0.1:8766`.

An open run-scoped decision pauses only its affected run. A global decision may
pause all work only for the global stop conditions in the binding design.
Archived or closed decisions do not block reconciliation.

A Reviewer timeout, capacity error, malformed response, or temporary outage is
recorded as `review_degraded`. When deterministic safety gates pass, safe runs
continue and review is retried at the next cadence. Reviewer infrastructure
failure does not create a user decision by itself.

## Migration and shadow gate

Dry-run first. It streams JSONL line by line, inventories protected dirty paths,
and does not remove legacy artifacts:

```bash
python3 -m scripts.loop_supervisor.cli migrate --project-root /home/fyz/codex-skills --dry-run
python3 -m scripts.loop_supervisor.cli shadow-compare --project-root /home/fyz/codex-skills
```

The shadow report must contain zero `new_user_intervention` and zero
`unsafe_divergence`. Apply only during the Task 10 cutover window, after stopping
the old executors:

```bash
python3 -m scripts.loop_supervisor.cli migrate --project-root /home/fyz/codex-skills
python3 -m scripts.loop_supervisor.cli shadow-compare --project-root /home/fyz/codex-skills
```

Apply writes a timestamped snapshot beside the repository, outside the Git
index, before importing. It validates streamed row counts, compacted
transitions, failure first/last/count, decision status, run projections, and
Reviewer cadence. Legacy cleanup is a separate guarded operation and is allowed
only after both validation and shadow comparison pass:

```bash
python3 -m scripts.loop_supervisor.cli migrate --project-root /home/fyz/codex-skills --cleanup-legacy
```

## Rollback and rebuild

For rollback, stop the new Supervisor and Worker, retain the failed database for
diagnosis, restore `.codex/loop-runs` and `.codex/supervisor` JSON artifacts from
the migration report's `snapshot_path`, then restart the old executor. Never use
`git reset`, `git clean`, or overwrite tracked wiki/crawler content during
rollback.

SQLite is rebuildable from retained run artifacts and migration streams. Stop
both new processes before running:

```bash
python3 -m scripts.loop_supervisor.cli rebuild-db --project-root /home/fyz/codex-skills --confirm
```

The command moves the existing database files to an external timestamped backup,
creates the schema, and reruns validated migration. Detailed operational history
can be compacted after the retention period:

```bash
python3 -m scripts.loop_supervisor.cli retention --project-root /home/fyz/codex-skills --retention-days 90
```

Retention aggregates expired detail and preserves active decisions, incomplete
review applications, open findings, and required recovery evidence.
