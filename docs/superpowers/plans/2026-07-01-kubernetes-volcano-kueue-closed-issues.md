# Kubernetes Volcano Kueue Closed Issues Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture closed GitHub issues for Kubernetes, Volcano, and Kueue into `ai_infra`, curate reusable wiki references, and configure monthly synchronization.

**Architecture:** Add a reproducible GitHub closed-issue corpus sync script that fetches issue pages, filters out pull requests, fetches issue comments, writes compressed raw evidence plus readable indexes/summaries, and verifies manifest integrity. Add monthly Crawler Workbench source profiles for future synchronization while keeping tokens in `GITHUB_TOKEN` only.

**Tech Stack:** Python standard library, GitHub REST API, gzip JSON raw evidence, Personal Wiki Markdown pages, existing Crawler Workbench `sources.yaml`, pytest, wiki CLI validation.

---

### Task 1: Register Task And Source Profiles

**Files:**
- Modify: `tasks.json`
- Modify: `.personal-wiki-workbench/sources.yaml`
- Modify: `personal-wiki/apps/crawler_workbench/config/sources.example.yaml`
- Test: `personal-wiki/apps/crawler_workbench/backend/tests/test_api.py`

- [x] Add `github-closed-issues-k8s-volcano-kueue-01` to `tasks.json` with `requires_eval=true`.
- [x] Add three trusted monthly GitHub source profiles:
  - `kubernetes-github-closed-issues`
  - `volcano-github-closed-issues`
  - `kueue-github-closed-issues`
- [x] Configure profiles with `type: github`, `schedule: monthly`, `run_policy: scheduled`, `auto_ingest: false`, `auth_required: true`, `auth_method: env_token`, `auth_ref: GITHUB_TOKEN`, `baseline_on_first_run: true`.
- [x] Add a backend API/profile test that asserts the three sources exist with monthly schedule and token auth metadata.
- [x] Run `cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_api.py::test_example_sources_include_daily_ai_infra_tracking_sources`.

### Task 2: Add Reproducible GitHub Corpus Sync CLI

**Files:**
- Create: `scripts/github_closed_issues_corpus.py`
- Create: `scripts/tests/test_github_closed_issues_corpus.py`

- [x] Write tests for repository slug normalization, Link header parsing, PR filtering, summary generation, and manifest verification.
- [x] Implement `scripts/github_closed_issues_corpus.py` with:
  - `run --repo-root --output-dir --repo owner/name --domain ai_infra --max-pages N`
  - `verify-manifest --repo-root --manifest --min-repos N`
  - `--include-comments` default enabled
  - `GITHUB_TOKEN` read from environment only
  - raw output under `personal-wiki/domains/ai_infra/raw/github/<slug>/`
- [x] Write for each repo:
  - `<slug>-closed-issues-api-pages.json.gz`
  - `<slug>-issue-comments-api-pages.json.gz`
  - `<slug>-closed-issues-with-comments.json.gz`
  - `<slug>-closed-issues-summary.json`
  - `<slug>-closed-issues-index.json`
  - `<slug>-closed-issues.ingest-plan.md`
- [x] Write run manifest to output dir with repo counts, raw paths, summary paths, and rate limit metadata.
- [x] Run `pytest -q scripts/tests/test_github_closed_issues_corpus.py`.

### Task 3: Run Initial Corpus Capture

**Files:**
- Create raw evidence under `personal-wiki/domains/ai_infra/raw/github/`
- Create manifest under `.codex/github-closed-issues/github-closed-issues-k8s-volcano-kueue-01/manifest.json`

- [x] Run the corpus CLI:
  - `env -u https_proxy -u http_proxy -u all_proxy -u HTTPS_PROXY -u HTTP_PROXY -u ALL_PROXY python3 scripts/github_closed_issues_corpus.py run --repo-root . --output-dir .codex/github-closed-issues/github-closed-issues-k8s-volcano-kueue-01 --repo kubernetes/kubernetes --repo volcano-sh/volcano --repo kubernetes-sigs/kueue --domain ai_infra --max-pages 1 --max-comment-issues 5`
  - The run used unauthenticated public API access because no valid `GITHUB_TOKEN` was available in the shell; summaries and manifest mark the corpus as partial.
- [x] If full Kubernetes backfill exceeds available time or rate limit, rerun with a documented page cap and mark the corpus summary as partial. The monthly source profiles remain in place for future synchronization.
- [x] Verify manifest:
  - `python3 scripts/github_closed_issues_corpus.py verify-manifest --repo-root . --manifest .codex/github-closed-issues/github-closed-issues-k8s-volcano-kueue-01/manifest.json --min-repos 3`

### Task 4: Curate Wiki Pages

**Files:**
- Create or modify: `personal-wiki/domains/ai_infra/wiki/projects/kubernetes.md`
- Create or modify: `personal-wiki/domains/ai_infra/wiki/projects/volcano.md`
- Create or modify: `personal-wiki/domains/ai_infra/wiki/projects/kueue.md`
- Create: `personal-wiki/domains/ai_infra/wiki/references/kubernetes-volcano-kueue-github-closed-issues.md`
- Modify: `personal-wiki/domains/ai_infra/ingest.md`
- Modify: `personal-wiki/domains/ai_infra/wiki/index.md`

- [x] Create project pages with concise project scope and links to the shared reference page.
- [x] Create shared reference page describing corpus scope, included repos, issue/comment counts, state_reason interpretation, raw evidence paths, and monthly sync source IDs.
- [x] Update `ingest.md` Done section with the new raw corpus and curated pages.
- [x] Rebuild index with `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki index ai_infra`.
- [x] Run `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra`.

### Task 5: Final Verification And Commit

**Files:**
- All changed files from tasks 1-4

- [x] Run backend/profile tests:
  - `cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_api.py tests/test_db_profiles.py tests/test_fetchers.py`
- [x] Run script tests:
  - `pytest -q scripts/tests/test_github_closed_issues_corpus.py`
- [x] Run wiki validation:
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra`
- [x] Run manifest verification:
  - `python3 scripts/github_closed_issues_corpus.py verify-manifest --repo-root . --manifest .codex/github-closed-issues/github-closed-issues-k8s-volcano-kueue-01/manifest.json --min-repos 3`
- [x] Update `progress.md`.
- [ ] Commit only this worktree's task-scoped files.
