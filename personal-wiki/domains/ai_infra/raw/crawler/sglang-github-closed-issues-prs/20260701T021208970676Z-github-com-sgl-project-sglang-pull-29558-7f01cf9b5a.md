---
source_id: sglang-github-closed-issues-prs
title: Fix pythonic signed literal parsing
canonical_url: https://github.com/sgl-project/sglang/pull/29558
captured_at: '2026-07-01T02:12:08.970676+00:00'
content_hash: 7f01cf9b5add540ab5851574dac93df858575da3e083a6a9ec291528bec7073f
---
# Fix pythonic signed literal parsing

URL: https://github.com/sgl-project/sglang/pull/29558
State: closed
Labels: 
Closed at: 2026-06-30T00:04:21Z
Merged at: 

## Summary

- parse pythonic tool-call signed numeric literals (`-5`, `+2`, nested signed list/dict values)
- preserve the existing literal-only guard for unsupported unary operands
- add a `TestPythonicDetector` regression covering two calls in the same pythonic list so one signed literal no longer drops the whole batch

## Root Cause

Python parses signed numeric literals as `ast.UnaryOp`, not `ast.Constant`. `PythonicDetector._get_parameter_value` only handled `ast.Constant`, `ast.Dict`, and `ast.List`, so a negative argument raised during parsing. The caller caught the exception and returned no tool calls.

Fixes #27910.

## Validation

- `python3 -m py_compile python/sglang/srt/function_call/pythonic_detector.py test/registered/unit/function_call/test_function_call_parser.py`
- `git diff --check`
- focused local check that loaded the modified `PythonicDetector` with stubbed dependencies and verified two calls survive `temperature=-5`, `delta=+2`, `bounds=[-1.5, +2.25]`, and `config={'offset': -3}`

Not run: full pytest target in this bare environment because pytest and SGLang runtime dependencies such as numpy are not installed.























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28346494010](https://github.com/sgl-project/sglang/actions/runs/28346494010)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28346493963](https://github.com/sgl-project/sglang/actions/runs/28346493963)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
