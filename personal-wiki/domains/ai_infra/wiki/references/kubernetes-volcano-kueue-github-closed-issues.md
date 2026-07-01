---
type: Reference
title: Kubernetes, Volcano, And Kueue GitHub Closed Issues
description: Local raw corpus and monthly sync setup for closed GitHub issues from Kubernetes, Volcano, and Kueue.
domain: ai_infra
status: reviewed
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

This reference indexes the local raw corpus for closed GitHub issues from `kubernetes/kubernetes`, `volcano-sh/volcano`, and `kubernetes-sigs/kueue`. The raw layer preserves GitHub API issue/search pages, issue-comment API pages, joined issue/comment records, summaries, indexes, and ingest plans.

The current backfill captures `volcano-sh/volcano` and `kubernetes-sigs/kueue` across their full closed-issue history, and captures `kubernetes/kubernetes` for issues closed on or after 2023-07-01. The Kubernetes window uses monthly GitHub Search ranges for issue discovery, while the all-time Volcano and Kueue backfills use the closed issues endpoint.

# Corpus Scope

| Repository | Issue pages | Closed issues | Comment pages | Comments | State reasons | Closed range | Partial reasons |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| `kubernetes/kubernetes` | 79 | 5,897 | 300 | 6,386 | `completed`: 4,506; `duplicate`: 13; `not_planned`: 1,378 | 2023-07-01 to 2026-06-30 | none; closed_at window starts 2023-07-01 |
| `volcano-sh/volcano` | 49 | 1,772 | 267 | 8,369 | `completed`: 1,760; `duplicate`: 1; `not_planned`: 11 | 2019-03-20 to 2026-06-30 | none |
| `kubernetes-sigs/kueue` | 122 | 2,488 | 300 | 6,650 | `completed`: 2,294; `duplicate`: 2; `not_planned`: 192 | 2022-02-18 to 2026-06-30 | none |

For Volcano and Kueue, the issue endpoint was queried with `state=closed`, `sort=updated`, and `direction=desc`, then pull requests were filtered out of the joined corpus and index. For Kubernetes, monthly Search API windows queried `repo:kubernetes/kubernetes is:issue is:closed closed:<month-range>` and the joined corpus keeps only issues whose `closed_at` is on or after 2023-07-01.

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

GitHub `state_reason` is workflow metadata. `completed`, `duplicate`, and `not_planned` all represent closed issues, but only the linked issue details and comments can show whether a closure corresponds to an implemented fix, duplicate handling, stale cleanup, design decision, or unsupported request.

The corpus script stores tokens only through the `GITHUB_TOKEN` environment variable. The combined run manifest is under `.codex/github-closed-issues/github-closed-issues-volcano-kueue-full-k8s-3y-01/manifest.json` and records rate-limit metadata, raw paths, and partial reasons for the run.

The successful backfill ran with proxy environment variables unset. The script retries transient GitHub read failures and uses repository-level issue-comment pages for comment joining instead of one request per issue.

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
