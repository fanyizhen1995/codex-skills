---
source_id: sglang-github-closed-issues-prs
title: '[CI] Add per-stage NVIDIA model inventory tool'
canonical_url: https://github.com/sgl-project/sglang/pull/29447
captured_at: '2026-07-04T02:13:49.139409+00:00'
content_hash: 89b4a0aef1bc6765d24f931464673dd99668eb5b66c1950cf7d951cad5bc89fa
---
# [CI] Add per-stage NVIDIA model inventory tool

URL: https://github.com/sgl-project/sglang/pull/29447
State: closed
Labels: 
Closed at: 2026-07-03T03:38:04Z
Merged at: 2026-07-03T03:38:04Z

## Motivation

There is currently no authoritative, machine-readable list of which models each NVIDIA (CUDA) CI suite exercises. This makes it hard to pre-warm runner model caches: a model that a suite pulls lazily at test time can cause a cold HuggingFace download (and the occasional rate-limit/timeout) far from where it'd be easy to diagnose.

This PR adds a small, dependency-free tool that statically derives `suite -> [HuggingFace model ids]` and publishes it as a CI artifact, refreshed per push to `main`.

## What it does

- **`scripts/ci/list_stage_models.py`** — reuses the existing AST registry parser (`ut_parse_one_file`, the same one `run_suite.py` uses) to map each suite to its registered test files, then statically resolves the models each file references:
  - a constant table built from `python/sglang/test/**/*.py` (`DEFAULT_*` model constants, incl. tuple values),
  - inline HuggingFace-id literals,
  - `ast.Name` references to known model constants.
  
  f-string fragments are skipped (they'd yield truncated, non-existent ids). The tool is **recall-favoring**: files it can't resolve a model for are listed per-suite as `unresolved_files`, and files it can't parse are surfaced in `parse_failures` — gaps are visible, never silently dropped. No sglang import, no GPU.
- **Per-runner-LABEL aggregation** (`runner_labels`) — registration/prewarm decisions are made per GH runner label (`runs-on`), not per suite: a runner registered under a label must have every model cached for **every** suite that can route to it, before the label is applied. Each suite's `runner_config` maps to its label via `scripts/ci/runner_configs.yml` (several configs share one label, e.g. `4-gpu-h100` + `deepep-4-gpu-h100`; parsed with a stdlib parser anchored to the real file by a unit test). `$b200_runner` stays literal unless `--b200-runner` substitutes it. Legacy `suite=` registrations (nightly/stress/weekly/jit-kernel) are mapped via a `suite_labels` override holding the label(s) their dispatching workflow hardcodes — a list, since `nightly-8-gpu-common` runs on two. Suites that genuinely have no GHA label (gb300 k8s-pod nightlies, undispatched `nightly-2-gpu`) stay visible in `unmapped_suites`.
- **`scripts/ci/stage_models_overrides.json`** — `by_file` / `by_suite` additions for dynamic cases the static scan can't see, a `deny` list for false positives, and the `suite_labels` map above.
- **`scripts/ci/test_list_stage_models.py`** — 25 stdlib-only unit tests (model-id heuristics, constant resolution, override merge, suite→files grouping, full `build_inventory` assembly via a fake-repo harness).
- **`.github/workflows/ci-model-inventory.yml`** — runs the tests, generates `models-per-stage.json`, writes a Markdown table to the job summary, and uploads the artifact. Triggers: `workflow_dispatch`, `push` to `main` (path-filtered), and a nightly `schedule` safety net. Runs on `ubuntu-latest` in seconds.

## How to consume

```bash
gh run download -R sgl-project/sglang --name models-per-stage   # -> models-per-stage.json
```
…or read the rendered table in the run's job summary.

### Output shape
```json
{
  "generated_at_commit": "<sha>",
  "backend": "cuda",
  "suite_count": 45,
  "model_count": 206,
  "runner_label_count": 9,
  "runner_labels": {
    "8-gpu-h200": {"models": ["..."], "suites": ["base-a-test-8-gpu-h200", "nightly-8-gpu-h200", "stress", "weekly-8-gpu-h200", "..."]}
  },
  "unmapped_suites": ["nightly-2-gpu", "nightly-4-gpu-gb300-..."],
  "all_models": ["..."],
  "parse_failures": {},
  "suites": {
    "base-c-test-4-gpu-b200": {
      "nightly": false,
      "models": ["nvidia/DeepSeek-V3-0324-FP4", "..."],
      "test_file_count": 14,
      "unresolved_files": ["test/registered/..."]
    }
  }
}
```

Current run against `main`: **45 enabled CUDA suites, 9 runner labels, 206 distinct models, 0 parse failures, 5 unmapped suites** (the gb300 k8s-pod nightlies + `nightly-2-gpu`). Disabled suites are excluded by default (they don't run → nothing to warm); `--include-disabled` surfaces them.

## Notes
- Draft: opening for early feedback on approach/scope before finalizing.
- Future-friendly: an authoritative `models=[...]` kwarg on `register_*_ci` could drive recall to 100% later; this PR intentionally starts with the zero-test-churn static scan.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28636334206](https://github.com/sgl-project/sglang/actions/runs/28636334206)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28636334121](https://github.com/sgl-project/sglang/actions/runs/28636334121)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
