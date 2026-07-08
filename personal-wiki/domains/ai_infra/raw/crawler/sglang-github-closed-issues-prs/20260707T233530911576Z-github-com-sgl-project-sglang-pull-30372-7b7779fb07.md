---
source_id: sglang-github-closed-issues-prs
title: '[fix] Fix two trunk test regressions due to flexkv change (#29701)'
canonical_url: https://github.com/sgl-project/sglang/pull/30372
captured_at: '2026-07-07T23:35:30.911576+00:00'
content_hash: 7b7779fb076fae43969d1df5955eb8f2ddc803a394654540c76bf01c7c35c785
---
# [fix] Fix two trunk test regressions due to flexkv change (#29701)

URL: https://github.com/sgl-project/sglang/pull/30372
State: closed
Labels: run-ci
Closed at: 2026-07-07T08:58:46Z
Merged at: 2026-07-07T08:58:46Z

## Motivation
Two `base-a-test-cpu` unit tests regressed on `main` after **#29701 (flexkv main connector)**:
- **`test_legacy_global_ratchet`** — the flexkv code introduced a `get_global_server_args()` call-site, growing the legacy-accessor count to **281 > baseline 280**. The ratchet is decrease-only: new code must use the `sglang.srt.runtime_context` accessors.
- **`test_fallback_to_radix_cache`** — #29701 added a flexkv branch to `default_radix_cache_factory`. The test's `MagicMock` `server_args` has a truthy `enable_flexkv` / `flexkv_config_file`, so it enters that branch and crashes on `os.environ["FLEXKV_CONFIG_PATH"] = <MagicMock>` (`TypeError: str expected, not MagicMock`).
This PR fixes both so trunk CI is green.
## Modifications
- **`flexkv_radix_cache.py`** — use `runtime_context.get_server_args()` instead of the legacy `get_global_server_args()` shim, restoring the ratchet count to its baseline (280). No baseline bump needed.
- **`test_registry.py`** — set `enable_flexkv=False` on the mocked `server_args` in `_make_ctx` so the fallback tests don't enter the flexkv branch, where a `MagicMock` `flexkv_config_file` crashed the `os.environ` assignment.

## Accuracy Tests
N/A — test-only + accessor swap; no model, kernel, or forward-path changes.

## Speed Tests and Profiling
N/A — no impact on the inference path.

## Checklist
- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process
1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28853501994](https://github.com/sgl-project/sglang/actions/runs/28853501994)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28853501576](https://github.com/sgl-project/sglang/actions/runs/28853501576)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
