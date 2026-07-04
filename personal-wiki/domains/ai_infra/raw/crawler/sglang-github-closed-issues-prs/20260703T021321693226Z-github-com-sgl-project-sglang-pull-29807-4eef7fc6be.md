---
source_id: sglang-github-closed-issues-prs
title: Add XPU CI job monitor workflow
canonical_url: https://github.com/sgl-project/sglang/pull/29807
captured_at: '2026-07-03T02:13:21.693226+00:00'
content_hash: 4eef7fc6be212a9c12732ecd75a7de813612f490142608251f66fdc111bf0d27
---
# Add XPU CI job monitor workflow

URL: https://github.com/sgl-project/sglang/pull/29807
State: closed
Labels: run-ci, run-ci-extra
Closed at: 2026-07-03T00:30:17Z
Merged at: 2026-07-03T00:30:17Z

## Summary

Adds `.github/workflows/xpu-ci-job-monitor.yml` — a daily observability workflow that produces per-job health reports for the Intel XPU CI (`pr-test-xpu.yml`).

Follows the same pattern as the existing job-monitor workflow for other backends, scoped to XPU:

- **Daily 00:00 UTC** cron run generates pass/fail counts, durations, and runner utilization over the last 24h
- **Per-job matrix reports** — one report per test job in `pr-test-xpu.yml` (currently `stage-a-test-1-gpu-xpu`, `stage-b-test-1-gpu-xpu`), discovered dynamically via `yq` so new stages are picked up automatically
- **Runner fleet report** — cross-job runner analytics for the Intel XPU fleet
- **Manual dispatch** — supports `hours` (window override) and `job_filter` (single-job custom report) inputs
- **Fork-PR and unlabeled-PR guard** — PR trigger runs only on same-repo PRs with the `run-ci` label, and uses a 20-min window so PRs touching this file (or `query_job_status.py`) get a cheap smoke test
- **Single API scan, shared artifact** — `fetch-actions-data` runs once and downstream jobs consume the snapshot to stay within GitHub API rate limits

No changes to how XPU CI itself runs. This is purely an observability layer on top of the existing `pr-test-xpu.yml`.

## Test plan

- [ ] YAML parses (verified locally with `yaml.safe_load`)
- [ ] `parse-workflows` step yields `[stage-a-test-1-gpu-xpu, stage-b-test-1-gpu-xpu]` when run against current `pr-test-xpu.yml` (verified locally)
- [ ] All `query_job_status.py` flags used exist in its `--help` output (verified locally)
- [ ] PR trigger fires this workflow via its own `paths:` filter — opening this PR should produce an end-to-end smoke run (requires `run-ci` label)
- [ ] After merge to `main`, confirm the first scheduled run at 00:00 UTC produces the expected report structure

🤖 Generated with [Claude Code](https://claude.com/claude-code)











































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28508488746](https://github.com/sgl-project/sglang/actions/runs/28508488746)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28508488531](https://github.com/sgl-project/sglang/actions/runs/28508488531)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
