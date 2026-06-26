# Ingest Plan

Source path: raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-with-comments.json.gz

## Source Scope

- Source repository: https://github.com/NVIDIA/nccl
- Captured query: closed GitHub issues, excluding pull requests.
- Full raw capture:
  - `raw/github/nvidia-nccl-closed-issues/api-pages/closed-issues-page-*.json.gz`
  - `raw/github/nvidia-nccl-closed-issues/comment-pages/issue-comments-page-*.json.gz`
  - `raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-api-pages.json.gz`
  - `raw/github/nvidia-nccl-closed-issues/nvidia-nccl-issue-comments-api-pages.json.gz`
  - `raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-with-comments.json.gz`
  - `raw/github/nvidia-nccl-closed-issues/nvidia-nccl-closed-issues-summary.json`
- Completeness check: 19 closed issue pages and 91 issue-comment pages were captured. The joined corpus contains 1,589 closed issues and 7,325 comments attached to those issues, with zero mismatch against the issue objects' comment counts.

## Candidate Page Updates

- Update `wiki/projects/nccl.md` with a concise operational issue-corpus entry and link to the reference page.
- Create `wiki/references/nccl-github-closed-issues.md` as the durable index and synthesis page for the closed issue corpus.
- Do not mirror individual issue bodies or discussions into `wiki/`; keep raw as the full evidence layer.

## Curated Claims To Preserve

- The closed issue corpus is operational evidence for troubleshooting, integration, and upgrade risk, complementary to official release notes.
- The captured closed issue set spans issues created from 2016-01-15 to 2026-06-22 and closed from 2016-01-25 to 2026-06-23.
- GitHub returned 1,850 closed issue-or-PR items; after excluding pull requests, the corpus has 1,589 closed issues.
- GitHub `state_reason` splits the included closed issues into 921 `completed` and 668 `not_planned` items.
- Labels are sparse in the repository's historical closed issue set, so label counts should not be treated as a complete taxonomy.
- Keyword-derived themes are useful retrieval aids but are not mutually exclusive and should not be read as strict issue classifications.

## Completion Criteria

- `wiki/projects/nccl.md` references the new issue-corpus reference.
- `wiki/references/nccl-github-closed-issues.md` cites the joined raw corpus and summary.
- `wiki/index.md` is rebuilt.
- Domain and full-repository validation pass.
