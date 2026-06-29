---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] nightly: track SGLang-Diffusion only'
canonical_url: https://github.com/sgl-project/sglang/pull/29434
captured_at: '2026-06-29T04:09:41.034336+00:00'
content_hash: 05a72bf329202fe4246778b8e6b7829eb144328b0b8446b8be776d4eb75d6039
---
# [diffusion] nightly: track SGLang-Diffusion only

URL: https://github.com/sgl-project/sglang/pull/29434
State: closed
Labels: run-ci, diffusion
Closed at: 2026-06-28T06:23:18Z
Merged at: 2026-06-28T06:23:18Z

## Motivation

The diffusion nightly test now tracks **SGLang-Diffusion itself** (regression over time) rather than comparing against other serving frameworks. This PR drops the cross-framework framing and refreshes the benchmark case list.

## Changes

**Naming** — the nightly no longer compares frameworks, so:
- Rename the job `nightly-test-diffusion-comparison` → `nightly-test-diffusion` (synchronized across the `workflow_dispatch` option, the `job_filter` guard, and the summary job's `needs` list).
- Drop "cross-framework" / "comparison" wording from the step name, artifact name, dashboard H1/H2 titles, and script docstrings / `--help` descriptions.
- Internal identifiers are kept as-is (`comparison-results.json`, the `diffusion-comparisons` ci-data storage prefix, function names) to avoid breaking historical data and widening the change surface. The runner still supports extra frameworks via `--frameworks`; only the nightly config tracks SGLang-Diffusion alone.

**Benchmark cases** (`comparison_configs.json`):
- ➖ Drop the LTX-2 (base) case.
- ✅ Keep LTX-2.3 (TI2V, TP2).
- ➕ Add Ideogram-4 — `ideogram-ai/ideogram-4-fp8`, fp8, TP2, text-to-image.
- ➕ Add Cosmos3-Super text-to-video — `nvidia/Cosmos3-Super`, TP2, 81 frames @ 720p, guardrails disabled (matches the `cosmos3_nano_t2v` gpu_case).

All newly added cases run multi-GPU (`num_gpus > 1`).

## Checklist
- [x] Workflow job-id references synchronized (dispatch option / `job_filter` / `needs`)
- [x] `comparison_configs.json` validated — 11 cases parse cleanly
- [x] No `cross-framework` wording remains in user-facing strings

🤖 Generated with [Claude Code](https://claude.com/claude-code)



















































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28311347150](https://github.com/sgl-project/sglang/actions/runs/28311347150)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28311347076](https://github.com/sgl-project/sglang/actions/runs/28311347076)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
