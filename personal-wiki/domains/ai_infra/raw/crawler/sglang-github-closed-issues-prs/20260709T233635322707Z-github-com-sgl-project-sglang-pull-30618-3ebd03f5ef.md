---
source_id: sglang-github-closed-issues-prs
title: Turn off  topk v2 for DSA models by default to avoid seldom IMA issues
canonical_url: https://github.com/sgl-project/sglang/pull/30618
captured_at: '2026-07-09T23:36:35.322707+00:00'
content_hash: 3ebd03f5ef08f43811563aaf49346546e864c4c16f6a5bf83c6d63c82bce3b2c
---
# Turn off  topk v2 for DSA models by default to avoid seldom IMA issues

URL: https://github.com/sgl-project/sglang/pull/30618
State: closed
Labels: 
Closed at: 2026-07-09T20:38:32Z
Merged at: 

## Summary
- Disable SGLANG_OPT_USE_TOPK_V2 for DSA models during model-specific server-args handling.
- Add server-args unit coverage for the DSA model env override.

## Tests
- pre-commit hooks from git commit: isort, ruff, black-jupyter, codespell, registered test registry checks, etc.
- /Users/baizhou.zhang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile python/sglang/srt/server_args.py test/registered/unit/server_args/test_server_args.py
- git diff --check

Note: targeted pytest/unittest could not run in this local environment because pytest and runtime deps such as orjson are not installed.





























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29011107637](https://github.com/sgl-project/sglang/actions/runs/29011107637)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29011107482](https://github.com/sgl-project/sglang/actions/runs/29011107482)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
