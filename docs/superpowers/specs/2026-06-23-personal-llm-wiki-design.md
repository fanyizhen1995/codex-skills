# Personal LLM-First Wiki Design

## Purpose

Build a personal wiki repository that combines OKF-style knowledge documents
with an LLM Wiki workflow. The repository is optimized for LLM/agent use first:
agents should be able to ingest source material, maintain structured knowledge,
answer questions with traceable sources, and evolve the wiki without scanning the
entire repository.

The design choices confirmed for the first version are:

- LLM-first usage.
- Raw source material and curated wiki pages live in the same repository.
- Knowledge is isolated by domain.
- Ingest is explicitly triggered by the user.
- The implementation roadmap must be written into the repository so later work
  is not lost after the initial skeleton is built.

## Architecture

The repository has three top-level responsibilities:

```text
personal-wiki/
  README.md
  WIKI.md
  ROADMAP.md
  docs/
  schemas/
  domains/
  global/
  tools/
```

`WIKI.md` is the global agent operating protocol. Any LLM working in the
repository reads it first.

`domains/` contains isolated domain bundles. Each domain is the default boundary
for ingest, search, and maintenance.

`global/` contains only genuinely shared knowledge: cross-domain concepts,
people, organizations, and reusable references.

`schemas/` contains machine-readable frontmatter and repository conventions when
validation tooling is added.

`tools/` contains local automation for validation, indexing, graph export,
ingest assistance, and snapshot helpers.

## Domain Layout

Each domain is an independent knowledge unit:

```text
domains/<domain>/
  DOMAIN.md
  ingest.md
  raw/
    inbox/
    links/
    notes/
    papers/
    images/
    snapshots/
  wiki/
    index.md
    assets/
      images/
    concepts/
    papers/
    projects/
    decisions/
    references/
```

`DOMAIN.md` defines the domain boundary, important terminology, preferred
reading order, common aliases, and any domain-specific rules.

`ingest.md` records pending and completed ingest work. It is both a queue and an
audit trail.

`raw/` stores source material. LLMs may organize it and add light metadata, but
must not rewrite it into polished conclusions.

`wiki/` stores curated OKF-style knowledge pages. These pages are the main
surface for LLM retrieval and reasoning.

## Raw Source Rules

Raw material is the fact source. Wiki pages are derived knowledge.

Raw files should remain close to the captured material. When an LLM converts a
PDF, web page, transcript, or screenshot into text, that derived extraction still
belongs under `raw/`, not directly under `wiki/`.

Raw markdown files use light frontmatter:

```yaml
---
type: RawSource
title: FlashAttention paper
source_kind: paper
url: https://example.com/paper.pdf
captured: 2026-06-23
status: pending
---
```

Recommended `source_kind` values are:

- `paper`
- `web`
- `note`
- `image`
- `snapshot`
- `transcript`
- `repository`

Recommended raw status values are:

- `pending`
- `ingested`
- `superseded`
- `archived`

LLMs do not delete raw sources during ingest. They either leave them in place,
move them from `raw/inbox/` to the correct raw subdirectory, or update their
status.

## Image Rules

Images are split into raw evidence and curated wiki assets.

```text
domains/<domain>/
  raw/
    images/
    snapshots/
  wiki/
    assets/
      images/
    references/
```

`raw/images/` stores original screenshots, paper figures, webpage images,
whiteboard photos, and other unmodified visual evidence.

`wiki/assets/images/` stores images intentionally used in wiki pages. These may
be cropped, compressed, renamed, or otherwise prepared for stable wiki use.

Wiki pages should normally reference `wiki/assets/images/`, not `raw/images/`.
Raw images are cited as evidence through `source_refs` or citations.

Important images get their own `Reference` page, for example:

```text
wiki/references/kv-cache-layout-diagram.md
```

That page describes what the image means, where it came from, which concepts it
supports, and which wiki asset file renders it. LLMs should read this reference
page before treating the image as structured knowledge.

Example image reference from a wiki page:

```markdown
![KV cache layout](../assets/images/kv-cache-layout.png)
```

## Wiki Page Types

The initial wiki page types are deliberately small:

- `Concept`: a concept, term, mechanism, pattern, or technique.
- `Paper`: a structured reading note for a paper, report, or long-form source.
- `Project`: a system, repository, product, implementation, or tool.
- `Decision`: a personal judgment, design choice, selection, or conclusion.
- `Reference`: reusable facts such as diagrams, commands, APIs, metrics,
  glossaries, checklists, and source collections.

All ordinary wiki pages use OKF-style frontmatter:

```yaml
---
type: Concept
title: KV Cache
description: Transformer inference uses KV cache to reuse attention key/value states across generated tokens.
domain: ai-infra
status: draft
tags: [llm-inference, transformer]
source_refs:
  - ../../raw/papers/example-paper.md
updated: 2026-06-23
---
```

Required fields:

- `type`
- `title`
- `description`
- `domain`

Recommended fields:

- `status`
- `tags`
- `source_refs`
- `updated`
- `aliases`
- `related`

Wiki status values:

- `draft`: useful but not fully reviewed.
- `reviewed`: explicitly reviewed by the user.
- `stale`: likely outdated or contradicted by newer material.
- `deprecated`: retained for history but no longer preferred.

Only the user can promote a page to `reviewed`. LLMs may suggest promotion but
must not do it silently.

## Wiki Body Conventions

The body remains Markdown and may vary by page type, but these sections are
preferred when applicable:

```markdown
# Summary

# Key Points

# Details

# Relationships

# Open Questions

# Citations
```

`description` stays one sentence because indexes and LLM routing depend on it.

New claims should cite raw files or external URLs. If sources conflict, the LLM
adds `# Conflicts` or `# Open Questions` instead of forcing a conclusion.

## Domain Indexes

`domains/<domain>/wiki/index.md` is the domain navigation entry:

```markdown
# AI Infra Wiki

## Concepts
- [KV Cache](concepts/kv-cache.md) - Transformer inference uses KV cache to reuse attention key/value states across generated tokens.

## Papers
- [Attention Is All You Need](papers/attention-is-all-you-need.md) - Reading note for the original Transformer paper.
```

Indexes should be concise. Their job is routing, not full explanation.

Index generation can start manually and later become automated with
`wiki index <domain>`.

## LLM Read Protocol

For any query or maintenance task, an LLM follows this order:

1. Read root `WIKI.md`.
2. Identify the target domain.
3. Read `domains/<domain>/DOMAIN.md`.
4. Read `domains/<domain>/wiki/index.md`.
5. Open specific wiki pages by following links or matching titles/tags.
6. Open raw sources only when validating or ingesting claims.
7. Avoid full-repository scans unless the user requests cross-domain research or
   validation.

The default context boundary is one domain. Cross-domain traversal must be
explicitly justified by the user request or by a direct link.

## Ingest Workflow

Ingest is explicitly triggered by the user. Example request:

```text
ingest domains/ai-infra/raw/inbox/flashattention.md
```

The LLM workflow is:

1. Read `WIKI.md`, the domain `DOMAIN.md`, and the domain `wiki/index.md`.
2. Read the target raw source.
3. Decide whether to create new wiki pages, update existing pages, or mark the
   source as not useful.
4. Check for existing similar concepts before creating new pages.
5. Create or update wiki pages incrementally.
6. Preserve and add `source_refs`.
7. Add citations for new claims.
8. For important images, create or update a `Reference` page.
9. Update `wiki/index.md`.
10. Update `ingest.md` with pending/done status and created/updated pages.
11. Run validation when tooling exists.

LLMs must not wholesale rewrite an existing page when augmenting it. They first
read the page, preserve useful structure, and add or revise the smallest section
that satisfies the ingest task.

## Cross-Domain Rules

Knowledge stays in the domain where it is primarily useful.

Use `global/wiki/` only for concepts, people, organizations, and references that
are truly reused across multiple domains.

Example global layout:

```text
global/wiki/
  index.md
  concepts/
  people/
  organizations/
  references/
```

Domain pages may link to global pages. From a page under
`domains/ai-infra/wiki/concepts/`, the relative path looks like:

```markdown
See [Transformer](../../../../global/wiki/concepts/transformer.md).
```

Domain pages may link directly to another domain when the target remains
domain-specific. From the same source directory, the relative path looks like:

```markdown
See [HAMi scheduler](../../../hami/wiki/projects/hami-scheduler.md).
```

LLMs should not move content into `global/` merely because it is interesting.
The concept should have recurring use across domains.

## Quality Control

The repository should eventually enforce these checks:

- Frontmatter is present and valid for all wiki pages.
- Required fields exist and are non-empty.
- `type` is one of the accepted page types.
- `status` is one of the accepted status values.
- `source_refs` paths exist when local.
- Markdown links resolve.
- Image paths resolve.
- Important wiki images have a nearby source reference or a `Reference` page.
- `wiki/index.md` includes all important pages.
- Duplicate titles and aliases are reported.
- `reviewed` pages have citations or source references.
- Raw sources marked `ingested` list their generated or updated wiki pages in
  `ingest.md`.

Quality checks should report problems before mutating files.

## Tooling Roadmap

The final system includes local tooling, but the file format remains the source
of truth. Tools should not require a database.

Planned commands:

```text
wiki init-domain <name>
wiki validate [--domain <name>]
wiki index <domain>
wiki backlinks [--domain <name>]
wiki graph [--domain <name>] [--out graph.json]
wiki snapshot-url <domain> <url>
wiki image-note <domain> <image-path>
wiki ingest-plan <domain> <raw-path>
```

`wiki init-domain` creates a domain skeleton from templates.

`wiki validate` runs the quality checks listed above.

`wiki index` rebuilds domain indexes from wiki page frontmatter.

`wiki backlinks` computes reverse links and can write reference sections or a
machine-readable backlink index.

`wiki graph` exports a knowledge graph for visualization or agent routing.

`wiki snapshot-url` captures a URL into `raw/links/` or `raw/snapshots/` with
metadata.

`wiki image-note` creates a `Reference` page template for an image.

`wiki ingest-plan` produces a proposed set of page changes without applying
them. This supports user review before larger ingests.

## Agent Skill Roadmap

After repository conventions and validation tools exist, create a Codex skill
named `personal-wiki-manager`.

The skill should route user requests into modes:

- `query`: answer from a domain wiki with citations.
- `ingest`: convert raw material into wiki updates.
- `validate`: run quality checks and summarize issues.
- `refactor`: merge duplicate concepts, rename pages, or update links.
- `create-domain`: scaffold a new domain.
- `image-note`: turn an important image into a referenced knowledge object.

The skill must enforce the LLM read protocol and default domain boundary.

## Implementation Phases

Phase 1: Repository specification and templates

- Create root `WIKI.md`.
- Create root `ROADMAP.md`.
- Create domain skeleton templates.
- Create wiki page templates.
- Create raw source templates.
- Document image rules.
- Document ingest rules.

Phase 2: Validation tooling

- Implement frontmatter validation.
- Implement link validation.
- Implement image reference validation.
- Implement source reference validation.
- Implement duplicate title and alias reporting.
- Add tests for validation behavior.

Phase 3: Index and graph tooling

- Implement domain index generation.
- Implement backlink extraction.
- Implement graph JSON export.
- Optionally generate a static HTML graph view.

Phase 4: Ingest assistance

- Implement `wiki ingest-plan` for proposed changes.
- Support raw markdown, URL snapshots, paper notes, and image notes.
- Update `ingest.md` consistently.
- Keep user confirmation before high-impact writes.

Phase 5: Codex skill

- Create `personal-wiki-manager` skill.
- Encode read protocol, ingest protocol, and validation expectations.
- Add mode-specific checklists.

Phase 6: Optional publication and visualization

- Add MkDocs, Quartz, or static HTML export if human browsing becomes more
  important.
- Add graph visualization using exported graph JSON.
- Keep publication optional so LLM-first workflows remain primary.

## Open Decisions

The following choices can be deferred without blocking the repository design:

- Exact implementation language for `tools/`; Python is the default unless the
  target wiki repo already has another toolchain.
- Whether to generate backlinks inline in pages or only as machine-readable
  metadata.
- Whether to use JSON Schema, a Python validator, or both for frontmatter.
- Whether URL snapshots store full HTML, cleaned Markdown, or both.
- Whether public publishing is needed.

## Acceptance Criteria

The first complete implementation is successful when:

- A new domain can be created from templates.
- Raw source material can be placed under the domain and explicitly ingested.
- Wiki pages use the agreed OKF-style frontmatter.
- Images follow raw versus curated asset rules.
- Domain indexes help LLMs route queries without scanning the full repository.
- Validation detects broken links, missing source references, bad frontmatter,
  and missing image assets.
- The roadmap for later automation and skill creation exists in the repository.
