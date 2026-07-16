---
source_id: sglang-github-closed-issues-prs
title: Add agent rule to all non-docs READMEs
canonical_url: https://github.com/sgl-project/sglang/pull/31095
captured_at: '2026-07-14T23:40:21.685553+00:00'
content_hash: f3c9ed363d82a5e3b58676e3b2dbb34793df06d7a07425e5ed5e57689859b21e
---
# Add agent rule to all non-docs READMEs

URL: https://github.com/sgl-project/sglang/pull/31095
State: closed
Labels: documentation, sgl-kernel, diffusion, model-gateway
Closed at: 2026-07-14T02:46:42Z
Merged at: 

## What changed
Appended the requested agent instruction to every tracked README outside `docs/` and `docs_new/`.

## Why
Makes the instruction visible across root, component, benchmark, example, and test README entry points.

## Validation
- Confirmed 94 targeted README files changed.
- Confirmed every targeted file ends with the exact requested text.
- Ran `git diff --check`.

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: **Missing `run-ci` label** -- add it to run CI tests.<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: **Blocked** -- `run-ci` is required first.<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
