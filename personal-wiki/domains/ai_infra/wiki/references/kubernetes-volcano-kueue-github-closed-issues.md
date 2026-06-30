---
type: Reference
title: Kubernetes, Volcano, And Kueue GitHub Closed Issues
description: Local raw corpus and monthly sync setup for closed GitHub issues from Kubernetes, Volcano, and Kueue.
domain: ai_infra
status: draft
tags:
  - kubernetes
  - volcano
  - kueue
  - github-issues
  - scheduling
source_refs:
  - ../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-summary.json
  - ../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-index.json
  - ../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-with-comments.json.gz
  - ../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-api-pages.json.gz
  - ../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-issue-comments-api-pages.json.gz
  - ../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-summary.json
  - ../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-index.json
  - ../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-with-comments.json.gz
  - ../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-api-pages.json.gz
  - ../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-issue-comments-api-pages.json.gz
  - ../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-summary.json
  - ../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-index.json
  - ../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-with-comments.json.gz
  - ../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-api-pages.json.gz
  - ../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-issue-comments-api-pages.json.gz
updated: 2026-07-01
aliases:
  - Kubernetes closed issue corpus
  - Volcano closed issue corpus
  - Kueue closed issue corpus
related:
  - ../projects/kubernetes.md
  - ../projects/volcano.md
  - ../projects/kueue.md
---
# Summary

This reference indexes the local raw corpus for closed GitHub issues from `kubernetes/kubernetes`, `volcano-sh/volcano`, and `kubernetes-sigs/kueue`. The raw layer preserves GitHub API issue pages, selected issue-comment API pages, joined issue/comment records, summaries, indexes, and ingest plans.

The first capture is a partial backfill, not a historical full corpus. It was run through the public GitHub API without a usable token, with `--max-pages 1 --max-comment-issues 5` for each repository. Treat it as a verified seed corpus and monthly synchronization setup.

# Corpus Scope

| Repository | Issue pages | Closed issues | Comment pages | Comments | State reasons | Closed range | Partial reasons |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| `kubernetes/kubernetes` | 1 | 25 | 5 | 36 | `completed`: 16; `not_planned`: 9 | 2018-01-16 to 2026-06-30 | `max_pages=1`; `max_comment_issues=5` |
| `volcano-sh/volcano` | 1 | 23 | 5 | 5 | `completed`: 23 | 2026-06-12 to 2026-06-30 | `max_pages=1`; `max_comment_issues=5` |
| `kubernetes-sigs/kueue` | 1 | 25 | 5 | 19 | `completed`: 21; `not_planned`: 4 | 2026-03-06 to 2026-06-30 | `max_pages=1`; `max_comment_issues=5` |

The issue endpoint was queried with `state=closed`, `sort=updated`, and `direction=desc`. Because this is updated-order capture, an older closed issue can appear in the seed corpus if it was updated recently.

# Raw Files

Kubernetes:

- [Summary](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-summary.json)
- [Index](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-index.json)
- [Joined issues and comments](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-with-comments.json.gz)
- [Closed issue API pages](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-api-pages.json.gz)
- [Issue comment API pages](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-issue-comments-api-pages.json.gz)

Volcano:

- [Summary](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-summary.json)
- [Index](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-index.json)
- [Joined issues and comments](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-with-comments.json.gz)
- [Closed issue API pages](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-api-pages.json.gz)
- [Issue comment API pages](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-issue-comments-api-pages.json.gz)

Kueue:

- [Summary](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-summary.json)
- [Index](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-index.json)
- [Joined issues and comments](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-with-comments.json.gz)
- [Closed issue API pages](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-api-pages.json.gz)
- [Issue comment API pages](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-issue-comments-api-pages.json.gz)

# Capture Notes

GitHub `state_reason` is workflow metadata. `completed` and `not_planned` both represent closed issues, but only the linked issue details and comments can show whether a closure corresponds to an implemented fix, duplicate handling, stale cleanup, design decision, or unsupported request.

The corpus script stores tokens only through the `GITHUB_TOKEN` environment variable. The run manifest is under `.codex/github-closed-issues/github-closed-issues-k8s-volcano-kueue-01/manifest.json` and records rate-limit metadata and partial reasons for the run.

The first network attempt through the local proxy failed during TLS handshake. The successful seed capture ran with proxy environment variables unset.

# Monthly Synchronization

Crawler Workbench source profiles are configured for monthly tracking:

| Source ID | Repository | Schedule | Auth |
| --- | --- | --- | --- |
| `kubernetes-github-closed-issues` | `kubernetes/kubernetes` | monthly | `GITHUB_TOKEN` environment token |
| `volcano-github-closed-issues` | `volcano-sh/volcano` | monthly | `GITHUB_TOKEN` environment token |
| `kueue-github-closed-issues` | `kubernetes-sigs/kueue` | monthly | `GITHUB_TOKEN` environment token |

The profile URLs include `state=closed` so monthly checks stay aligned with the closed-issue corpus scope.

# Retrieval Notes

Use the summary JSON files for counts, `state_reason` splits, top labels, and capture limits. Use the index JSON files for quick issue lookup by number, title, URL, labels, state reason, close time, and attached comment count. Use the joined `.json.gz` files when comment text or full GitHub issue objects are needed.

# Relationships

- [Kubernetes](../projects/kubernetes.md) is the upstream orchestration project page.
- [Volcano](../projects/volcano.md) is the batch scheduling project page.
- [Kueue](../projects/kueue.md) is the job queueing project page.

# Citations

- [Kubernetes closed issues summary](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-summary.json)
- [Kubernetes joined issues and comments](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-with-comments.json.gz)
- [Volcano closed issues summary](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-summary.json)
- [Volcano joined issues and comments](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-with-comments.json.gz)
- [Kueue closed issues summary](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-summary.json)
- [Kueue joined issues and comments](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-with-comments.json.gz)
