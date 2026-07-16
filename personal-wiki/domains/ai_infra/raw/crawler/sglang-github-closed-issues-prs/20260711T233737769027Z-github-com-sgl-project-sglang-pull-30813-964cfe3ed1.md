---
source_id: sglang-github-closed-issues-prs
title: 'ci: prune uv cache in job teardown to bound its growth'
canonical_url: https://github.com/sgl-project/sglang/pull/30813
captured_at: '2026-07-11T23:37:37.769027+00:00'
content_hash: 964cfe3ed19c0f614f607b5948c6233af4465860f77e01b0c62ad77bd03ea24e
---
# ci: prune uv cache in job teardown to bound its growth

URL: https://github.com/sgl-project/sglang/pull/30813
State: closed
Labels: high priority, run-ci
Closed at: 2026-07-11T10:01:23Z
Merged at: 2026-07-11T10:01:23Z

The persistent uv cache (`~/.cache/uv`, bind-mounted and shared across all runner containers) has no eviction, so it grows unbounded. On the 5090 hosts it reached ~500 GB and filled the root disk, failing jobs with ENOSPC at dependency install (`failed to write to file ... os error 28`).

Add a best-effort prune to the `always()` teardown, **gated on disk usage (>=85%)** so it's a pressure valve, not a routine tax:
- Healthy jobs pay only a `df` check — the cache is left intact, so nothing is re-downloaded or recompiled on the next install.
- Under pressure, `uv cache prune --ci` reclaims space; it keeps downloaded wheels + sdist archives (no re-download) and drops built wheels (a later install may recompile source-built packages, which is acceptable only when the disk is actually filling).

Runs in teardown (off the install critical path), regardless of venv mode; never fails the job.























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29124935407](https://github.com/sgl-project/sglang/actions/runs/29124935407)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #29125166967](https://github.com/sgl-project/sglang/actions/runs/29125166967)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
