# Wiki Agent Protocol

This repository is optimized for LLM and agent use. Follow this protocol for
query, ingest, maintenance, and refactoring work.

## Read Order

1. Read this `WIKI.md`.
2. Identify the target domain.
3. Read `domains/<domain>/DOMAIN.md`.
4. Read `domains/<domain>/wiki/index.md`.
5. Open specific wiki pages by following links or matching titles, aliases, and tags.
6. Open raw sources only when validating or ingesting claims.

Avoid full-repository scans unless the user explicitly asks for cross-domain
research, repository-wide validation, or duplicate detection.

## Knowledge Layers

raw/ is the fact source. It contains captured sources, notes, transcripts,
paper extractions, screenshots, snapshots, and raw image evidence.

wiki/ is the curated knowledge layer. It contains OKF-style Markdown pages
with YAML frontmatter, concise descriptions, links, and citations.

Do not rewrite raw sources into polished conclusions. Create or update wiki
pages instead.

## Domain Boundary

The default context boundary is one domain under `domains/<domain>/`.

Use `global/wiki/` only for concepts, people, organizations, and references that
are reused across multiple domains.

Cross-domain links must be explicit. Do not move content into `global/` merely
because it is interesting.

## Ingest Rules

Ingest is explicitly triggered by the user. A typical request names a raw file,
for example:

```text
ingest domains/ai-infra/raw/inbox/flashattention.md
```

Before creating a new wiki page, check the domain index and nearby pages for an
existing concept. Prefer updating existing pages over creating duplicates.

When updating a page:

- Preserve useful existing structure.
- Add or revise the smallest section that satisfies the task.
- Preserve existing `source_refs`.
- Add citations for new claims.
- Update `ingest.md`.

Do not promote a page to reviewed unless the user explicitly asks.

## Image Rules

`raw/images/` stores original visual evidence.

`wiki/assets/images/` stores curated images that wiki pages reference.

Wiki pages should normally reference `wiki/assets/images/`, not `raw/images/`.
Important images should have a `Reference` page that explains image meaning,
image source, and supported concepts.

## Source Integrity

New factual claims need a `source_refs` entry or a citation. If sources conflict,
add `# Conflicts` or `# Open Questions` instead of forcing a conclusion.

When answering the user, cite wiki paths and raw source paths when they are used.
