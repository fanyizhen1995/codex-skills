---
source_id: sglang-github-closed-issues-prs
title: 'ci: run jit-kernel tests on scheduled full runs'
canonical_url: https://github.com/sgl-project/sglang/pull/30306
captured_at: '2026-07-07T23:35:30.915245+00:00'
content_hash: 7a8e85abebc2d025df28469303d4823ebbdd1e0baac659c5eeddaaf717444aeb
---
# ci: run jit-kernel tests on scheduled full runs

URL: https://github.com/sgl-project/sglang/pull/30306
State: closed
Labels: 
Closed at: 2026-07-07T07:14:39Z
Merged at: 2026-07-07T07:14:39Z

## Motivation

The jit-kernel suite (`pr-test-jit-kernel.yml`) only ran on PRs that touch `python/sglang/jit_kernel/**`. The 3x-daily scheduled full run skipped it via an explicit `github.event_name != 'schedule'` guard on `call-jit-kernel-tests`, so regressions on `main` from unrelated changes went uncaught until a jit_kernel PR happened to run.

## Change

Gate `call-jit-kernel-tests` the same way as the `base-*` stages so it runs on scheduled / parallel-dispatch runs (`check-changes` already forces `jit_kernel='true'` on scheduled runs via `run_all_tests`).

On scheduled / parallel-dispatch runs `sgl-kernel-build-wheels` is skipped, so the wheel artifact the jit-kernel jobs download (`if: inputs.sgl_kernel == 'true'`) does not exist and they would fail. To avoid that, force `sgl_kernel='false'` for the jit-kernel call on those runs, so the jobs skip the wheel download and test against the released/pinned sgl-kernel instead of a fresh build. This keeps the scheduled run from also triggering the 20-30 min wheel build.

## Effect

- Adds the jit-kernel jobs (`1-gpu-h100`, `8-gpu-h200`, `4-gpu-b200`) to every scheduled full run; jit-kernel failures now surface in the scheduled `pr-test-finish` gate.
- PR behavior is unchanged (still runs only when `jit_kernel/**` changes).

## Validation

Triggered a `workflow_dispatch` with `test_parallel_dispatch=true` + `run_all_tests=true` (the built-in scheduled-run simulation) on this branch to confirm `call-jit-kernel-tests` dispatches and passes on the scheduled path.





















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28828864531](https://github.com/sgl-project/sglang/actions/runs/28828864531)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28828864450](https://github.com/sgl-project/sglang/actions/runs/28828864450)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
