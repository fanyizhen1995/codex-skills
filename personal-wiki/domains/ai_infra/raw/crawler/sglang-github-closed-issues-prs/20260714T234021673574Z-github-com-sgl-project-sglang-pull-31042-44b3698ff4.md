---
source_id: sglang-github-closed-issues-prs
title: '[CI] Fix SGLANG_JIT_KERNEL_RUN_FULL_TESTS never activating the nightly full
  jit-kernel sweep'
canonical_url: https://github.com/sgl-project/sglang/pull/31042
captured_at: '2026-07-14T23:40:21.673574+00:00'
content_hash: 44b3698ff4e93d50a32d4ffff748413eb119cc5fea8d66aee301f99ba285a0c5
---
# [CI] Fix SGLANG_JIT_KERNEL_RUN_FULL_TESTS never activating the nightly full jit-kernel sweep

URL: https://github.com/sgl-project/sglang/pull/31042
State: closed
Labels: ci, run-ci, jit-kernel
Closed at: 2026-07-14T09:32:30Z
Merged at: 2026-07-14T09:32:29Z

## Motivation

Found while investigating the `test_custom_all_reduce.py` nightly timeout in #30999: `nightly-test-nvidia.yml` sets `SGLANG_JIT_KERNEL_RUN_FULL_TESTS: "1"` for the two "JIT kernel full unit tests" jobs, but `should_run_full_tests()` compared the raw string against `"true"` only:

```python
def should_run_full_tests() -> bool:
    return os.getenv(_FULL_TEST_ENV_VAR, "false").lower() == "true"   # "1" -> False
```

So the nightly full-sweep expansion has **never actually been active** — those jobs have silently run the same reduced grids as PR CI since they were added.

## Modifications

- `python/sglang/srt/environ.py`: register `SGLANG_JIT_KERNEL_RUN_FULL_TESTS = EnvBool(False)` in the `# SGLang CI` section, per env-var conventions.
- `python/sglang/jit_kernel/utils.py`: `should_run_full_tests()` reads it via `envs....get()` — `EnvBool` accepts `1/true/yes` (case-insensitive), and a malformed value now raises instead of silently meaning "false". Removes the last raw `os.getenv` read of this variable.
- `.github/workflows/nightly-test-nvidia.yml`: since this genuinely activates the expanded grids, give the 8-GPU nightly kernel suite an explicit `--timeout-per-file 3600`. The full custom-all-reduce sweep runs ~7x the in-CI parametrizations per world size, which cannot fit the 1200s default (measured reduced sweep on a slow H200 runner: 98s @ 2 GPUs / 209s @ 4 GPUs / ~620s @ 8 GPUs — data from #30999's logging). The 1-gpu suite keeps the default budget; job-level `timeout-minutes` are unchanged and remain the backstop.

## Heads-up for reviewers

This makes the two nightly kernel jobs actually do what their name says, so their wall-clock will increase accordingly (that was the stated intent when they were added — it just never fired). #30999 additionally scales `test_custom_all_reduce`'s per-torchrun budget when the full sweep is active, and its cache/phase-timing logs will attribute any remaining nightly timeout. If the expanded runtime turns out to be more than the nightly capacity wants to pay, dialing back is a one-line change to the job env — but that should be an explicit decision rather than a string-parsing accident.

## Validation

```
$ SGLANG_JIT_KERNEL_RUN_FULL_TESTS=1 python -c 'from sglang.jit_kernel.utils import should_run_full_tests, get_ci_test_range; print(should_run_full_tests(), get_ci_test_range([1,2,3,4,5],[1,2]))'
True [1, 2, 3, 4, 5]
# 'true'/'TRUE' -> True; '0'/'false'/unset -> False; reduced range still returned in CI when unset
```

## Checklist

- [x] Format your code with pre-commit
- [x] Add unit tests (N/A — 3-line env-var registration + parsing fix, exercised by every jit-kernel CI job)
- [x] Update documentation (N/A)

🤖 Generated with [Claude Code](https://claude.com/claude-code)























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29302992107](https://github.com/sgl-project/sglang/actions/runs/29302992107)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29302991987](https://github.com/sgl-project/sglang/actions/runs/29302991987)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
