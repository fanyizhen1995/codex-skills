---
source_id: sglang-github-closed-issues-prs
title: '[misc] Add unit test admission criteria to agent rules'
canonical_url: https://github.com/sgl-project/sglang/pull/30608
captured_at: '2026-07-09T23:36:35.338573+00:00'
content_hash: d9c9c87d951b22b5e883d9a1131937fbc7b59e0bfd54f0abf0e43f66be78610b
---
# [misc] Add unit test admission criteria to agent rules

URL: https://github.com/sgl-project/sglang/pull/30608
State: closed
Labels: documentation
Closed at: 2026-07-09T06:41:48Z
Merged at: 2026-07-09T06:41:48Z

Adds a path-scoped agent rule (`.claude/rules/unit-test-admission.md`, injected only when touching `test/**/*.py`) defining which unit test cases are worth writing: bug regressions verified against the pre-fix code, derived properties, and critical-path bookkeeping -- and rejecting happy-path tautologies, mirror tests, and stress loops with no reproducing power.









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28999219329](https://github.com/sgl-project/sglang/actions/runs/28999219329)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28999219114](https://github.com/sgl-project/sglang/actions/runs/28999219114)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
