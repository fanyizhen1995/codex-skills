---
name: scuda-fresh-performance-runbook
description: Use when running or preparing SCUDA benchmark, profile, correctness, native/same-host/cross-host, artifact sync, checksum, cleanup, matrix, or fresh endpoint experiments, before drawing performance conclusions.
---

# SCUDA Fresh Performance Runbook

## Core Rule

A SCUDA performance run is valid only if the endpoint, artifacts, workload mode, evidence class, and cleanup state are fresh and traceable. Use `scuda-performance-evidence-review` for conclusions; this skill governs execution.

## Workflow

1. Start from canonical root unless the user names a worktree. Read `AGENTS.md`, `docs/ENVIRONMENT_RUNBOOK.md`, `docs/issue-ledger.md`, `progress.md`, `tasks.json`, target design/plan, `git status --short --branch`, and recent commits.
2. Define the evidence class before running: correctness, benchmark-only, profile, smoke, or debug clue. Do not compare profile-mode throughput with benchmark-only throughput.
3. Preflight:
   - clean or verify no stale `server_*.so`, SCUDA clients, `:26040`, `/tmp/scuda_*.sock`, or `/dev/shm/scuda_cq*`;
   - build in CUDA devel container unless the task explicitly allows host build;
   - sync paired `libscuda_*.so` and `server_*.so` to remote when needed;
   - record local/remote checksums and exact build dirs.
4. Run via existing project scripts first: `test/pytorch_imagenet_resnet_dummy_matrix.sh`, `test/pytorch_correctness_matrix.sh`, focused smoke scripts, or newer task-specific matrix scripts. Use `long-running-experiment` and `codex-engineering-context-optimizer` for long/log-heavy runs.
5. Parse accepted evidence: require `SCUDA_MATRIX_STATUS=OK`, expected report files, fallback/timeout/peer_close counters, profile counters relevant to the gate, and workload-specific benchmark rows.
6. Classify failures separately: workload failure, parser/completeness failure, stale endpoint, artifact mismatch, cleanup failure, Docker/container lifecycle, or design expectation mismatch.
7. Cleanup and prove it with a fresh local and remote scan. If cleanup fails, the run is not closed.
8. Update `progress.md`, `sprint_output.md`, and `docs/issue-ledger.md` when the run changes conclusions, exposes a recurring failure, or affects defaultization.

## Output

Use concise Chinese:

- `运行口径`: workload, mode, paths, labels, env, native/same/cross.
- `产物`: output dir, wrapper meta, checksum, report/log paths.
- `结果`: accepted/rejected and why.
- `性能/Profile`: only metrics valid for this evidence class.
- `清理`: before/after scan result.
- `下一步`: one rerun, one instrumentation/code target, one provenance safeguard.

## Common Mistakes

- Do not reuse old endpoints or old remote artifacts for a fresh run.
- Do not accept same-host results unless remote client and server artifacts are paired.
- Do not treat wrapper `exit_code=1` as workload failure until case logs and parser requirements are separated.
- Do not defaultize from a single positive profile counter or one benchmark sample.
- Do not claim cleanup complete when scan output self-matches, errors, or leaves orphan SHM/socket/process state.
