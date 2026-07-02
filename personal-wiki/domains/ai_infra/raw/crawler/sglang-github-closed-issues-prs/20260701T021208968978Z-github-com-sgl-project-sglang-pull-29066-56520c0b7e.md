---
source_id: sglang-github-closed-issues-prs
title: '[CI] Migrate JIT tests to runner config registration'
canonical_url: https://github.com/sgl-project/sglang/pull/29066
captured_at: '2026-07-01T02:12:08.968978+00:00'
content_hash: 56520c0b7ea42816d9651434602392a244bfe00043631b3e876b18f9b45aca9c
---
# [CI] Migrate JIT tests to runner config registration

URL: https://github.com/sgl-project/sglang/pull/29066
State: closed
Labels: documentation, quant, amd, lora, deepseek, hicache, blackwell, run-ci
Closed at: 2026-06-30T02:12:15Z
Merged at: 2026-06-30T02:12:15Z

## Summary
- Migrate JIT kernel CI registrations from legacy `suite=` strings to explicit `stage=` and `runner_config=` metadata.
- Rename the JIT kernel suite entries and workflow invocations to the generated `<stage>-test-<runner_config>` form so `run_suite.py` and `/rerun-test` use the same model.
- Remove the `/rerun-test` legacy suite-to-runner mapping so CUDA dispatch resolves runner details directly from `runner_config`.

## Test plan
- `python3 scripts/ci/check_registered_tests.py`
- Parsed registered tests and validated migrated CUDA/AMD JIT suite counts
- Validated `detect_suite()` resolution for representative JIT unit, B200, 8-GPU, and attention registrations
- `ReadLints` on edited Python paths
- Pre-commit hooks on commit

Made with [Cursor](https://cursor.com)











































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28212558820](https://github.com/sgl-project/sglang/actions/runs/28212558820)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28212558739](https://github.com/sgl-project/sglang/actions/runs/28212558739)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
