---
source_id: sglang-github-closed-issues-prs
title: '[CI] Fix model inventory for nested test model tables'
canonical_url: https://github.com/sgl-project/sglang/pull/30509
captured_at: '2026-07-09T23:36:35.333244+00:00'
content_hash: ba523c9b43d13a12624687622d5ba21264c6525c2db2bbcf47451e5423fecc67
---
# [CI] Fix model inventory for nested test model tables

URL: https://github.com/sgl-project/sglang/pull/30509
State: closed
Labels: 
Closed at: 2026-07-09T09:17:17Z
Merged at: 

## Motivation

The CI model inventory extractor currently misses model ids stored in nested static helper tables. One concrete case is `python/sglang/test/lora_utils.py`, where LoRA test cases are defined as `LoRAModelCase(base=..., adaptors=[...])` entries and registered tests reference the table by name. Because the constant table only handled direct string/list/tuple values, some LoRA base/adaptor model ids were omitted from the prewarm inventory.

## Modifications

- Recursively collect static string constants from assignment RHS nodes when building the model constant table.
- Keep f-string literal fragments excluded so dynamic/partial model ids are not accidentally captured.
- Add regression coverage for nested dataclass/dict-style model tables and nested f-string fragments.

## Accuracy Tests

Not applicable. This only changes CI static analysis for model inventory generation and does not affect runtime model outputs.

## Speed Tests and Profiling

Not applicable. This does not affect inference runtime.

## Tests

- `python3 -m unittest discover -s scripts/ci -p 'test_list_stage_models.py'`
- `python3 -m compileall -q scripts/ci/list_stage_models.py scripts/ci/test_list_stage_models.py`
- `/tmp/sglang-check-tools/bin/ruff check scripts/ci/list_stage_models.py scripts/ci/test_list_stage_models.py`
- `PYTHONPATH=/tmp/sglang-check-tools /tmp/sglang-check-tools/bin/codespell --config .codespellrc scripts/ci/list_stage_models.py scripts/ci/test_list_stage_models.py`
- `python3 scripts/ci/check_registered_tests.py`
- `python3 scripts/ci/check_workflow_job_names.py`
- `git diff --check`

Inventory sanity checks:

- CUDA inventory: distinct models `207 -> 209`, unresolved files `417 -> 412`, parse failures `0`
- AMD inventory: distinct models `148 -> 150`, unresolved files `169 -> 165`, parse failures `0`









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28930440306](https://github.com/sgl-project/sglang/actions/runs/28930440306)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28930440125](https://github.com/sgl-project/sglang/actions/runs/28930440125)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
