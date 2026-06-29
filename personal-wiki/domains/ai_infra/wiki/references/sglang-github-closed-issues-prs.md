---
type: Reference
title: SGLang GitHub Closed Issues And PRs
description: Local raw corpus and curated operational signals from closed sgl-project/sglang GitHub issues, pull requests, comments, and review comments.
domain: ai_infra
status: reviewed
tags:
  - sglang
  - github-issues
  - github-pull-requests
  - inference-serving
  - model-runtime
source_refs:
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-with-comments.split-manifest.json
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-summary.json
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-api-pages.json.gz
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-pulls-api-pages.json.gz
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-api-pages.json.gz
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-updated-segment-api-pages.json.gz
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-by-item-api-pages.json.gz
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-pr-review-comments-api-pages.json.gz
  - ../../raw/crawler/sglang-github-closed-issues-prs/manifest.json
updated: 2026-06-29
aliases:
  - sgl-project/sglang closed issues
  - sgl-project/sglang closed PRs
  - SGLang issue and PR corpus
related:
  - ../projects/sglang.md
---
# Summary

This reference indexes the local raw corpus for closed issues and closed pull requests in `sgl-project/sglang`. The raw layer preserves GitHub API pages, joined issue/PR objects, timeline comments, PR review comments, supplement pages used to work around repository-level issue-comment pagination boundaries, and a small crawler supplement captured after the API corpus cutoff. The curated layer keeps only scope, retrieval guidance, and operational signals.

# Corpus Scope

| Item | Value |
| --- | --- |
| Repository | `sgl-project/sglang` |
| Included source | Closed GitHub issues and closed GitHub pull requests |
| Issue endpoint capture | 252 pages, 25,108 mixed issue/PR items |
| Closed issues included | 5,633 |
| Pull request endpoint capture | 195 pages |
| Closed pull requests included | 19,475 |
| Merged PRs | 14,670 |
| Closed-unmerged PRs | 4,805 |
| Issue/PR timeline comments attached | 76,373 |
| PR review comments attached | 46,819 |
| Issue created range | 2024-01-13 to 2026-06-24 |
| Issue closed range | 2024-01-16 to 2026-06-24 |
| PR created range | 2024-01-08 to 2026-06-24 |
| PR closed range | 2024-01-08 to 2026-06-24 |
| Crawler supplement capture | 51 Markdown page snapshots captured 2026-06-29 |
| Crawler supplement overlap | 10 items overlap the API corpus; 41 are later selected page captures |

Raw files:

- [Joined closed issue/PR corpus](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-with-comments.split-manifest.json)
- [Derived summary](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-summary.json)
- [Raw index](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-index.json)
- [Closed issues endpoint pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-api-pages.json.gz)
- [Closed pulls endpoint pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-pulls-api-pages.json.gz)
- [Issue comments created-order pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-api-pages.json.gz)
- [Issue comments updated-segment pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-updated-segment-api-pages.json.gz)
- [Issue comments per-item supplement pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-by-item-api-pages.json.gz)
- [PR review comment pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-pr-review-comments-api-pages.json.gz)
- [Crawler supplement manifest](../../raw/crawler/sglang-github-closed-issues-prs/manifest.json)

# Capture Notes

The repository-level issue-comment API hit the page-300 boundary in created order. The raw corpus therefore supplements it with updated-order segment pages and per-item comment pages. After this supplementation, 17 closed items still have a mismatch between GitHub's `comments` count field and the visible comments returned by the item's comments API. These 17 items were re-fetched individually and are recorded as residual GitHub API visibility/count differences, not as an untried capture gap.

Unattached comment counts are expected in repository-level comment streams because some comments belong to open items, deleted/inaccessible items, or items outside this closed corpus filter. The joined corpus attaches only comments whose item number is included in the closed issue or closed PR set.

The crawler supplement under `raw/crawler/sglang-github-closed-issues-prs/` is selective browser/page evidence, not a replacement for the API corpus. Its manifest records 51 Markdown captures: 7 issue pages and 44 pull request pages. Ten captured item numbers already exist in the API corpus; 41 are later selected page captures, mostly closed between 2026-06-25 and 2026-06-29. Do not combine those 41 items into the API corpus counts unless a full API refresh with comments and review comments is performed.

# Operational Signals

The issue workflow state is mostly completed: 5,585 closed issues are `completed`, 35 are `not_planned`, and 13 are `duplicate`. Treat issue `state_reason` as workflow metadata, not as a direct quality or severity signal.

The highest-count issue labels are `inactive`, `high priority`, `bug`, `good first issue`, `help wanted`, `deepseek`, `enhancement`, `npu`, `collaboration`, `amd`, `router`, and `Multi-modal`. The highest-count PR labels include `run-ci`, `documentation`, `high priority`, `diffusion`, `deepseek`, `npu`, `amd`, `quant`, `model-gateway`, `dependencies`, `sgl-kernel`, and `Multi-modal`.

Keyword-derived themes are retrieval aids rather than mutually exclusive taxonomy. In the captured corpus, frequent surfaces include distributed parallelism and cluster behavior, serving runtime/API work, model support, kernel/attention backend work, memory and KV cache behavior, installation/build/packaging, performance, and reliability/correctness.

# Retrieval Notes

Use the joined raw corpus for exact lookup by issue or PR number. Use the summary JSON for aggregate counts, theme examples, label counts, top-discussed items, and capture caveats.

High-discussion examples in the captured corpus include:

| Item | Kind | Comments | Topic |
| --- | --- | ---: | --- |
| #6017 | Issue | 564 | DeepSeek large-scale P/D and expert-parallel instructions |
| #25144 | PR | 281 | Ascend NPU support for DeepSeek-V4 |
| #19746 | PR | 210 | P/D disaggregation decode-side radix cache |
| #21569 | PR | 177 | Transformers upgrade and Hugging Face utility refactor |
| #12263 | PR | 129 | EPD disaggregation support |
| #4848 | PR | 128 | Server-based rollout in Verlengine |
| #18306 | PR | 114 | SGLang-D diffusion weight update support |
| #22217 | PR | 113 | Eagle beta test failure debugging |
| #19225 | PR | 111 | Stable Diffusion 3 backend support |
| #27196 | PR | 107 | Pickle to msgpack migration |

# Relationships

- [SGLang](../projects/sglang.md) is the curated project page for this runtime and serving project.

# Citations

- [SGLang closed issues and PRs with comments](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-with-comments.split-manifest.json)
- [SGLang closed issues and PRs summary](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-summary.json)
- [SGLang closed issue API pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-api-pages.json.gz)
- [SGLang closed pull request API pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-pulls-api-pages.json.gz)
- [SGLang issue comment created-order pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-api-pages.json.gz)
- [SGLang issue comment updated-segment pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-updated-segment-api-pages.json.gz)
- [SGLang issue comment per-item supplement pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-by-item-api-pages.json.gz)
- [SGLang PR review comment pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-pr-review-comments-api-pages.json.gz)
- [SGLang crawler supplement manifest](../../raw/crawler/sglang-github-closed-issues-prs/manifest.json)
