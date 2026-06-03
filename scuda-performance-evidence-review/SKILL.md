---
name: scuda-performance-evidence-review
description: Use when reviewing SCUDA performance, benchmark, profile, native/same-host/cross-host comparisons, CQV2 or streaming gate failures, profile counters, report.md/summary.json artifacts, provenance, cleanup state, or progress charts before drawing optimization conclusions.
---

# SCUDA Performance Evidence Review

## Core Rule

Treat performance claims as evidence review, not log summarization. A conclusion is valid only when benchmark numbers, profile counters, artifact provenance, and cleanup state agree.

## Boundary With Execution Runs

- Use `scuda-fresh-performance-runbook` first when the task is to prepare or run a fresh benchmark/profile/correctness experiment, sync artifacts, clean endpoints, or create new evidence.
- Use this skill when evidence already exists, when deciding whether numbers are acceptable, or when classifying a performance conclusion.
- If review finds stale endpoints, mismatched artifacts, missing checksums, mixed evidence classes, or unproven cleanup, stop the conclusion and hand the next action back to `scuda-fresh-performance-runbook`.

## Workflow

1. Start in the canonical SCUDA root unless the user names a worktree. Read `AGENTS.md`, `docs/ENVIRONMENT_RUNBOOK.md`, `docs/issue-ledger.md`, `progress.md`, `tasks.json`, `git status --short --branch`, and recent commits.
2. Identify the evidence set: `summary.json`, `report.md`, benchmark logs, profile logs, profile parser output, smoke scripts, and the design/plan that defines the gate.
3. Verify provenance before numbers: client/server paths, checksums, local/remote build dirs, endpoint, client mode, runtime image, fresh server, and exact same-host/cross-host target.
4. Separate accepted evidence from clues:
   - Accepted throughput: fresh benchmark-only runs with correctness/import smoke.
   - Clues only: profile-mode throughput, isolated single samples, raw `wait_ns` snippets, stale endpoint runs, or mismatched artifacts.
5. Compare native, default/default_selected, same-host, cross-host, and candidate path using the same workload and accepted run class. Report native percentage and regression/upgrade direction.
6. Read profile counters only after the benchmark comparison. Check fallback/timeout/peer_close first, then batching/drain/write/read counters and server-side API gap counters.
7. Classify the failure as implementation bug, stale/invalid evidence, design expectation mismatch, missing optimization, or inconclusive. Tie the classification to specific files and metrics.
8. Finish with minimal next actions: one verification rerun, one code or instrumentation target if needed, and one cleanup/provenance safeguard.

## Output

Use concise Chinese unless the user asks otherwise:

- `证据范围`: artifact paths and accepted/rejected evidence.
- `性能结论`: same-host/cross-host vs native and baseline.
- `Profile 结论`: fallback/timeout/peer_close and key counters.
- `归因`: implementation/design/missing-optimization/inconclusive.
- `下一步`: 3-5 concrete commands or files to inspect.

## Common Mistakes

- Do not compare profile-mode throughput with benchmark-only throughput.
- Do not accept same-host results unless remote client and server artifacts are paired.
- Do not treat old sockets, old server processes, or unclean `/tmp/scuda_*` state as fresh evidence.
- Do not repair invalid evidence inside the review by silently rerunning pieces; switch to the fresh runbook and create a new traceable evidence set.
- Do not claim performance progress from a chart unless the underlying artifact paths are still traceable.
- Do not rerun long benchmarks without first defining success criteria, timeout, output directory, and cleanup plan.

## Useful Existing Tools

Use existing project tooling first: SCUDA test/report scripts, `long-running-experiment` for long runs, and `codex-engineering-context-optimizer` for large logs. This skill adds the review sequence and evidence acceptance rules; it does not replace those tools.
