---
source_id: sglang-github-closed-issues-prs
title: Handle psutil memory probe failures in ZMQ setup
canonical_url: https://github.com/sgl-project/sglang/pull/30477
captured_at: '2026-07-08T23:36:33.795212+00:00'
content_hash: 8b2804f5f9e951255daffa7ecdf3770b57ab57a1ba0ac92422b1912bbce07565
---
# Handle psutil memory probe failures in ZMQ setup

URL: https://github.com/sgl-project/sglang/pull/30477
State: closed
Labels: run-ci
Closed at: 2026-07-08T07:49:26Z
Merged at: 

## Summary

Fixes a GB300 CI startup failure where `psutil.virtual_memory()` can raise while parsing `/proc/meminfo`, aborting ZeroMQ socket setup before the server starts.

The ZMQ buffer size decision is only a best-effort memory heuristic, so this falls back to the existing conservative/default buffer behavior (`-1`) when memory probing fails.

## Root Cause

On the failing `base-c-test-4-gpu-gb300` job, `psutil.virtual_memory()` raised `ValueError: invalid literal for int() with base 10: b'kB'` from its Linux meminfo parser. `config_socket()` did not handle that, so tokenizer manager IPC setup crashed before tests ran.

## Validation

- `python -m py_compile python/sglang/srt/utils/network.py test/registered/unit/utils/test_network.py`
- Isolated local repro for `config_socket()` with `psutil.virtual_memory()` mocked to raise the CI `ValueError`
- Commit hooks: Python AST, isort, ruff, CI registry validation, and other pre-commit checks

Full registered test execution needs the normal SGLang CI environment because package-level imports pull the full runtime stack.













<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28920949419](https://github.com/sgl-project/sglang/actions/runs/28920949419)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28920989308](https://github.com/sgl-project/sglang/actions/runs/28920989308)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
