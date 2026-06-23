# Personal LLM Wiki Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1 scaffold for a personal LLM-first wiki repository, including global protocols, domain templates, raw/wiki/page templates, image rules, and a roadmap that preserves later development work.

**Architecture:** Create a standalone `personal-wiki/` scaffold inside the current workspace instead of changing the `codex-skills` repository root protocol. The scaffold is file-first: Markdown protocols and templates are the source of truth, with a small smoke test that verifies the expected structure and key template content.

**Tech Stack:** Markdown, Git, Bash, Python standard library for smoke tests.

---

## Scope

This plan implements Phase 1 from `docs/superpowers/specs/2026-06-23-personal-llm-wiki-design.md`.

It intentionally does not implement validation, indexing, graph export, ingest automation, URL snapshotting, or the Codex skill. Those are captured in `personal-wiki/ROADMAP.md` as follow-up phases with acceptance criteria.

## File Map

- Create: `personal-wiki/README.md`  
  Human entry point explaining what the scaffold is and how to start a domain.

- Create: `personal-wiki/WIKI.md`  
  Global LLM operating protocol: read order, source boundaries, ingest behavior, image rules, and cross-domain rules.

- Create: `personal-wiki/ROADMAP.md`  
  Full multi-phase roadmap copied into the target wiki scaffold so later work is not lost.

- Create: `personal-wiki/docs/design.md`  
  Local copy of the design summary for users who open only the generated scaffold.

- Create: `personal-wiki/schemas/frontmatter.md`  
  Human-readable schema for raw and wiki frontmatter. Phase 2 can convert this to JSON Schema or Python validation.

- Create: `personal-wiki/templates/domain/DOMAIN.md`  
  Domain protocol template.

- Create: `personal-wiki/templates/domain/ingest.md`  
  Ingest queue and audit log template.

- Create: `personal-wiki/templates/domain/wiki/index.md`  
  Domain wiki index template.

- Create: `personal-wiki/templates/wiki/concept.md`  
  `Concept` page template.

- Create: `personal-wiki/templates/wiki/paper.md`  
  `Paper` page template.

- Create: `personal-wiki/templates/wiki/project.md`  
  `Project` page template.

- Create: `personal-wiki/templates/wiki/decision.md`  
  `Decision` page template.

- Create: `personal-wiki/templates/wiki/reference.md`  
  `Reference` page template, including image reference guidance.

- Create: `personal-wiki/templates/raw/source.md`  
  Raw source template.

- Create: `personal-wiki/templates/raw/image-source.md`  
  Raw image metadata template.

- Create: `personal-wiki/global/wiki/index.md`  
  Global shared knowledge index.

- Create: `personal-wiki/global/wiki/concepts/.gitkeep`
- Create: `personal-wiki/global/wiki/people/.gitkeep`
- Create: `personal-wiki/global/wiki/organizations/.gitkeep`
- Create: `personal-wiki/global/wiki/references/.gitkeep`

- Create: `personal-wiki/domains/.gitkeep`
  Keeps the empty domain container in git until real domains are created.

- Create: `personal-wiki/tools/README.md`
  Concrete tool roadmap and command contract. This is documentation only, not fake implementation.

- Create: `personal-wiki/tests/test_scaffold.py`
  Smoke tests for required files, required template strings, and roadmap phases.

## Task 1: Add Failing Scaffold Smoke Tests

**Files:**
- Create: `personal-wiki/tests/test_scaffold.py`

- [ ] **Step 1: Create the test directory**

Run:

```bash
mkdir -p personal-wiki/tests
```

Expected: command exits 0.

- [ ] **Step 2: Create the test file**

Use `apply_patch` to create `personal-wiki/tests/test_scaffold.py` with this exact content:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_required_scaffold_files_exist():
    required = [
        "README.md",
        "WIKI.md",
        "ROADMAP.md",
        "docs/design.md",
        "schemas/frontmatter.md",
        "templates/domain/DOMAIN.md",
        "templates/domain/ingest.md",
        "templates/domain/wiki/index.md",
        "templates/wiki/concept.md",
        "templates/wiki/paper.md",
        "templates/wiki/project.md",
        "templates/wiki/decision.md",
        "templates/wiki/reference.md",
        "templates/raw/source.md",
        "templates/raw/image-source.md",
        "global/wiki/index.md",
        "global/wiki/concepts/.gitkeep",
        "global/wiki/people/.gitkeep",
        "global/wiki/organizations/.gitkeep",
        "global/wiki/references/.gitkeep",
        "domains/.gitkeep",
        "tools/README.md",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert missing == []


def test_global_llm_protocol_contains_core_rules():
    text = read("WIKI.md")
    assert "Read Order" in text
    assert "raw/ is the fact source" in text
    assert "wiki/ is the curated knowledge layer" in text
    assert "Do not promote a page to reviewed unless the user explicitly asks" in text
    assert "Avoid full-repository scans" in text


def test_frontmatter_schema_documents_required_fields():
    text = read("schemas/frontmatter.md")
    assert "Required wiki fields" in text
    assert "`type`" in text
    assert "`title`" in text
    assert "`description`" in text
    assert "`domain`" in text
    assert "RawSource" in text


def test_page_templates_include_source_refs_and_status():
    for path in [
        "templates/wiki/concept.md",
        "templates/wiki/paper.md",
        "templates/wiki/project.md",
        "templates/wiki/decision.md",
        "templates/wiki/reference.md",
    ]:
        text = read(path)
        assert "source_refs:" in text, path
        assert "status: draft" in text, path
        assert "# Citations" in text, path


def test_image_rules_are_represented_in_reference_template():
    text = read("templates/wiki/reference.md")
    assert "wiki/assets/images/" in text
    assert "raw/images/" in text
    assert "Image Meaning" in text
    assert "Image Source" in text


def test_roadmap_preserves_later_phases():
    text = read("ROADMAP.md")
    for phrase in [
        "Phase 2: Validation tooling",
        "Phase 3: Index and graph tooling",
        "Phase 4: Ingest assistance",
        "Phase 5: Codex skill",
        "Phase 6: Optional publication and visualization",
    ]:
        assert phrase in text
```

- [ ] **Step 3: Run the test and confirm it fails**

Run:

```bash
python -m pytest personal-wiki/tests/test_scaffold.py -q
```

Expected: FAIL because `personal-wiki/README.md` and the other scaffold files do not exist yet.

- [ ] **Step 4: Commit the failing test**

Run:

```bash
git add personal-wiki/tests/test_scaffold.py
git commit -m "test: add personal wiki scaffold smoke tests"
```

Expected: commit succeeds and includes only `personal-wiki/tests/test_scaffold.py`.

## Task 2: Add Global Scaffold Documents

**Files:**
- Create: `personal-wiki/README.md`
- Create: `personal-wiki/WIKI.md`
- Create: `personal-wiki/ROADMAP.md`
- Create: `personal-wiki/docs/design.md`
- Create: `personal-wiki/schemas/frontmatter.md`

- [ ] **Step 1: Create global scaffold directories**

Run:

```bash
mkdir -p personal-wiki/docs personal-wiki/schemas
```

Expected: command exits 0.

- [ ] **Step 2: Create `personal-wiki/README.md`**

Use `apply_patch` to create `personal-wiki/README.md`:

````markdown
# Personal Wiki

This repository is a personal LLM-first wiki scaffold. It combines OKF-style
Markdown knowledge documents with an LLM Wiki workflow.

The repository keeps raw source material and curated wiki pages together:

- `raw/` is the fact source.
- `wiki/` is the curated knowledge layer.
- `domains/` isolates knowledge by topic area.
- `global/` stores only knowledge reused across multiple domains.

Start by creating a domain from the templates in `templates/domain/`.

Recommended first domain layout:

```text
domains/<domain>/
  DOMAIN.md
  ingest.md
  raw/
  wiki/
```

Agents must read `WIKI.md` before maintaining this repository.
````

- [ ] **Step 3: Create `personal-wiki/WIKI.md`**

Use `apply_patch` to create `personal-wiki/WIKI.md`:

````markdown
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

`raw/` is the fact source. It contains captured sources, notes, transcripts,
paper extractions, screenshots, snapshots, and raw image evidence.

`wiki/` is the curated knowledge layer. It contains OKF-style Markdown pages
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
````

- [ ] **Step 4: Create `personal-wiki/ROADMAP.md`**

Use `apply_patch` to create `personal-wiki/ROADMAP.md`:

````markdown
# Personal Wiki Roadmap

This roadmap preserves the complete implementation plan beyond the initial
scaffold.

## Phase 1: Repository specification and templates

Acceptance criteria:

- Root `WIKI.md` exists and defines the LLM read protocol.
- Root `ROADMAP.md` preserves later phases.
- Domain templates exist.
- Wiki page templates exist for Concept, Paper, Project, Decision, and Reference.
- Raw source templates exist.
- Image storage and image reference rules are documented.

## Phase 2: Validation tooling

Build `wiki validate [--domain <name>]`.

Acceptance criteria:

- Frontmatter is parsed for all wiki pages.
- Required fields are checked.
- Accepted `type` and `status` values are enforced.
- Local `source_refs` paths are checked.
- Markdown links are checked.
- Image paths are checked.
- Duplicate titles and aliases are reported.
- `reviewed` pages without citations or source references are reported.

## Phase 3: Index and graph tooling

Build:

```text
wiki index <domain>
wiki backlinks [--domain <name>]
wiki graph [--domain <name>] [--out graph.json]
```

Acceptance criteria:

- Domain index generation uses page frontmatter.
- Backlink extraction handles relative Markdown links.
- Graph export includes nodes, links, page types, tags, and descriptions.

## Phase 4: Ingest assistance

Build:

```text
wiki snapshot-url <domain> <url>
wiki image-note <domain> <image-path>
wiki ingest-plan <domain> <raw-path>
```

Acceptance criteria:

- URL snapshots become raw sources with metadata.
- Important images can get Reference page drafts.
- Ingest plans propose changes without applying them.
- `ingest.md` is updated consistently after approved changes.

## Phase 5: Codex skill

Create a `personal-wiki-manager` Codex skill.

Acceptance criteria:

- The skill routes query, ingest, validate, refactor, create-domain, and
  image-note requests.
- The skill enforces the read protocol in `WIKI.md`.
- The skill respects domain boundaries by default.

## Phase 6: Optional publication and visualization

Add optional human-facing outputs only after LLM-first workflows are stable.

Possible outputs:

- Static graph HTML.
- MkDocs or Quartz publication.
- Obsidian compatibility notes.
````

- [ ] **Step 5: Create `personal-wiki/docs/design.md`**

Use `apply_patch` to create `personal-wiki/docs/design.md`:

```markdown
# Personal LLM Wiki Design Summary

This scaffold implements a personal wiki that combines OKF-style knowledge
documents with an LLM Wiki workflow.

The key design boundary is:

- `raw/` stores facts and captured source material.
- `wiki/` stores curated, linked, LLM-readable knowledge.

Each domain is isolated under `domains/<domain>/`. Agents should work inside one
domain by default and cross domains only when the user asks or a direct link
requires it.

Wiki pages use Markdown with YAML frontmatter. The frontmatter provides routing
metadata for agents and later tooling. The body remains readable Markdown with
citations and links.

Images are split into:

- `raw/images/` for original visual evidence.
- `wiki/assets/images/` for curated wiki display assets.

Important images should have `Reference` pages so LLMs can read their meaning
without relying on visual inference alone.
```

- [ ] **Step 6: Create `personal-wiki/schemas/frontmatter.md`**

Use `apply_patch` to create `personal-wiki/schemas/frontmatter.md`:

```markdown
# Frontmatter Schema

This file is the human-readable schema for Phase 1. Phase 2 validation tooling
can convert these rules into JSON Schema, Python checks, or both.

## Required wiki fields

- `type`: one of `Concept`, `Paper`, `Project`, `Decision`, `Reference`.
- `title`: short human-readable title.
- `description`: one sentence used for routing and indexes.
- `domain`: domain directory name, such as `ai-infra`.

## Recommended wiki fields

- `status`: one of `draft`, `reviewed`, `stale`, `deprecated`.
- `tags`: YAML list of short search tags.
- `source_refs`: YAML list of local raw paths or external URLs.
- `updated`: ISO date, such as `2026-06-23`.
- `aliases`: YAML list of alternate names.
- `related`: YAML list of related wiki paths.

## RawSource fields

Raw markdown files should use:

- `type: RawSource`
- `title`: source title.
- `source_kind`: one of `paper`, `web`, `note`, `image`, `snapshot`, `transcript`, `repository`.
- `url`: source URL when available.
- `captured`: ISO date when captured.
- `status`: one of `pending`, `ingested`, `superseded`, `archived`.

## Promotion rule

Only the user can promote a wiki page to `reviewed`.
```

- [ ] **Step 7: Run the scaffold test and confirm remaining failures**

Run:

```bash
python -m pytest personal-wiki/tests/test_scaffold.py -q
```

Expected: FAIL because template files, `global/`, `domains/.gitkeep`, and
`tools/README.md` are not created yet. The global protocol and frontmatter tests
should now pass.

- [ ] **Step 8: Commit global scaffold documents**

Run:

```bash
git add personal-wiki/README.md personal-wiki/WIKI.md personal-wiki/ROADMAP.md personal-wiki/docs/design.md personal-wiki/schemas/frontmatter.md
git commit -m "docs: add personal wiki global scaffold"
```

Expected: commit succeeds with only the five global scaffold documents.

## Task 3: Add Domain and Page Templates

**Files:**
- Create: `personal-wiki/templates/domain/DOMAIN.md`
- Create: `personal-wiki/templates/domain/ingest.md`
- Create: `personal-wiki/templates/domain/wiki/index.md`
- Create: `personal-wiki/templates/wiki/concept.md`
- Create: `personal-wiki/templates/wiki/paper.md`
- Create: `personal-wiki/templates/wiki/project.md`
- Create: `personal-wiki/templates/wiki/decision.md`
- Create: `personal-wiki/templates/wiki/reference.md`
- Create: `personal-wiki/templates/raw/source.md`
- Create: `personal-wiki/templates/raw/image-source.md`

- [ ] **Step 1: Create template directories**

Run:

```bash
mkdir -p personal-wiki/templates/domain/wiki personal-wiki/templates/wiki personal-wiki/templates/raw
```

Expected: command exits 0.

- [ ] **Step 2: Create `personal-wiki/templates/domain/DOMAIN.md`**

Use `apply_patch` to create `personal-wiki/templates/domain/DOMAIN.md`:

```markdown
# <Domain Name>

## Boundary

Describe what belongs in this domain and what does not.

## Read Order

1. Read this `DOMAIN.md`.
2. Read `wiki/index.md`.
3. Open specific wiki pages by following links.
4. Open raw sources only when validating or ingesting claims.

## Core Topics

- <topic>

## Common Aliases

- <alias> -> <canonical page>

## Ingest Notes

Raw sources enter through `raw/inbox/` unless they already fit a specific raw
subdirectory.

When ingesting, update `ingest.md` and preserve source references.

## Domain-Specific Rules

- Keep domain-specific rules here.
```

- [ ] **Step 3: Create `personal-wiki/templates/domain/ingest.md`**

Use `apply_patch` to create `personal-wiki/templates/domain/ingest.md`:

```markdown
# Ingest Log

## Pending

- [ ] `raw/inbox/example.md` - Describe expected wiki output.

## In Progress

No active ingest.

## Done

- [x] `raw/example.md` -> `wiki/concepts/example.md`

## Rejected

No rejected sources.
```

- [ ] **Step 4: Create `personal-wiki/templates/domain/wiki/index.md`**

Use `apply_patch` to create `personal-wiki/templates/domain/wiki/index.md`:

```markdown
# <Domain Name> Wiki

## Concepts

- [Example Concept](concepts/example.md) - One sentence description.

## Papers

- [Example Paper](papers/example-paper.md) - One sentence description.

## Projects

- [Example Project](projects/example-project.md) - One sentence description.

## Decisions

- [Example Decision](decisions/example-decision.md) - One sentence description.

## References

- [Example Reference](references/example-reference.md) - One sentence description.
```

- [ ] **Step 5: Create `personal-wiki/templates/wiki/concept.md`**

Use `apply_patch` to create `personal-wiki/templates/wiki/concept.md`:

```markdown
---
type: Concept
title: <Concept Title>
description: <One sentence description.>
domain: <domain>
status: draft
tags: []
source_refs: []
updated: 2026-06-23
aliases: []
related: []
---

# Summary

Explain the concept in one short paragraph.

# Key Points

- Point one.

# Details

Add domain-specific details.

# Relationships

- Related pages belong here.

# Open Questions

- Unknowns or conflicts belong here.

# Citations

- Add raw source paths or external URLs.
```

- [ ] **Step 6: Create `personal-wiki/templates/wiki/paper.md`**

Use `apply_patch` to create `personal-wiki/templates/wiki/paper.md`:

```markdown
---
type: Paper
title: <Paper Title>
description: <One sentence description.>
domain: <domain>
status: draft
tags: []
source_refs: []
updated: 2026-06-23
aliases: []
related: []
---

# Summary

Summarize the paper's problem, method, and conclusion.

# Key Points

- Main contribution.

# Method

Describe the method or system.

# Results

Capture concrete results and limitations.

# Relationships

- Link related concepts, projects, and references.

# Open Questions

- Note claims that need follow-up.

# Citations

- Add raw source paths or external URLs.
```

- [ ] **Step 7: Create `personal-wiki/templates/wiki/project.md`**

Use `apply_patch` to create `personal-wiki/templates/wiki/project.md`:

```markdown
---
type: Project
title: <Project Title>
description: <One sentence description.>
domain: <domain>
status: draft
tags: []
source_refs: []
updated: 2026-06-23
aliases: []
related: []
---

# Summary

Describe what the project is and why it matters.

# Architecture

Describe major components and boundaries.

# Usage

Record commands, workflows, or integration points.

# Relationships

- Link related concepts, papers, decisions, and references.

# Open Questions

- Note uncertainties.

# Citations

- Add raw source paths or external URLs.
```

- [ ] **Step 8: Create `personal-wiki/templates/wiki/decision.md`**

Use `apply_patch` to create `personal-wiki/templates/wiki/decision.md`:

```markdown
---
type: Decision
title: <Decision Title>
description: <One sentence description.>
domain: <domain>
status: draft
tags: []
source_refs: []
updated: 2026-06-23
aliases: []
related: []
---

# Summary

State the decision and outcome.

# Context

Describe why the decision was needed.

# Options

- Option A.
- Option B.

# Decision

Record the selected option and rationale.

# Follow-Up

- Verification or revisit items.

# Citations

- Add raw source paths or external URLs.
```

- [ ] **Step 9: Create `personal-wiki/templates/wiki/reference.md`**

Use `apply_patch` to create `personal-wiki/templates/wiki/reference.md`:

````markdown
---
type: Reference
title: <Reference Title>
description: <One sentence description.>
domain: <domain>
status: draft
tags: []
source_refs: []
updated: 2026-06-23
aliases: []
related: []
---

# Summary

Describe what this reference provides.

# Reference Content

Add commands, API details, glossary entries, metrics, diagrams, or source lists.

# Image Meaning

Use this section when the reference explains an important image.

Curated wiki image path:

```text
wiki/assets/images/<image-name>.png
```

# Image Source

Original raw image path:

```text
raw/images/<source-image-name>.png
```

# Relationships

- Link pages that use this reference.

# Citations

- Add raw source paths or external URLs.
````

- [ ] **Step 10: Create `personal-wiki/templates/raw/source.md`**

Use `apply_patch` to create `personal-wiki/templates/raw/source.md`:

```markdown
---
type: RawSource
title: <Source Title>
source_kind: note
url:
captured: 2026-06-23
status: pending
---

# Raw Content

Paste or extract source material here. Keep it close to the captured source.

# Capture Notes

- Add context about where this source came from.
```

- [ ] **Step 11: Create `personal-wiki/templates/raw/image-source.md`**

Use `apply_patch` to create `personal-wiki/templates/raw/image-source.md`:

```markdown
---
type: RawSource
title: <Image Source Title>
source_kind: image
url:
captured: 2026-06-23
status: pending
image_path: raw/images/<image-name>.png
---

# Raw Image Notes

Describe where the image came from and what context was captured with it.

# Expected Wiki Use

If this image becomes important knowledge, create a `Reference` page and a
curated copy under `wiki/assets/images/`.
```

- [ ] **Step 12: Run the scaffold test and confirm remaining failures**

Run:

```bash
python -m pytest personal-wiki/tests/test_scaffold.py -q
```

Expected: FAIL because `global/wiki/index.md`, `.gitkeep` files,
`domains/.gitkeep`, and `tools/README.md` are not created yet. Template-related
tests should now pass.

- [ ] **Step 13: Commit templates**

Run:

```bash
git add personal-wiki/templates
git commit -m "docs: add personal wiki templates"
```

Expected: commit succeeds with only files under `personal-wiki/templates/`.

## Task 4: Add Global Containers and Tool Roadmap

**Files:**
- Create: `personal-wiki/global/wiki/index.md`
- Create: `personal-wiki/global/wiki/concepts/.gitkeep`
- Create: `personal-wiki/global/wiki/people/.gitkeep`
- Create: `personal-wiki/global/wiki/organizations/.gitkeep`
- Create: `personal-wiki/global/wiki/references/.gitkeep`
- Create: `personal-wiki/domains/.gitkeep`
- Create: `personal-wiki/tools/README.md`

- [ ] **Step 1: Create global and domain directories**

Run:

```bash
mkdir -p personal-wiki/global/wiki/concepts personal-wiki/global/wiki/people personal-wiki/global/wiki/organizations personal-wiki/global/wiki/references personal-wiki/domains personal-wiki/tools
```

Expected: command exits 0.

- [ ] **Step 2: Create global and domain keep files**

Run:

```bash
touch personal-wiki/global/wiki/concepts/.gitkeep personal-wiki/global/wiki/people/.gitkeep personal-wiki/global/wiki/organizations/.gitkeep personal-wiki/global/wiki/references/.gitkeep personal-wiki/domains/.gitkeep
```

Expected: command exits 0 and the `.gitkeep` files are empty.

- [ ] **Step 3: Create `personal-wiki/global/wiki/index.md`**

Use `apply_patch` to create `personal-wiki/global/wiki/index.md`:

```markdown
# Global Wiki

Use this area only for knowledge reused across multiple domains.

## Concepts

No global concepts yet.

## People

No people pages yet.

## Organizations

No organization pages yet.

## References

No global references yet.
```

- [ ] **Step 4: Create `personal-wiki/tools/README.md`**

Use `apply_patch` to create `personal-wiki/tools/README.md`:

````markdown
# Tools Roadmap

This directory will contain local tooling for the personal wiki. Phase 1 does
not include executable tools.

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

Tooling principles:

- The filesystem remains the source of truth.
- Commands should report validation issues before mutating files.
- Commands should be testable without network access unless they explicitly
  snapshot URLs.
- Tools should work one domain at a time by default.
````

- [ ] **Step 5: Run the scaffold test and verify it passes**

Run:

```bash
python -m pytest personal-wiki/tests/test_scaffold.py -q
```

Expected: PASS with all six tests passing.

- [ ] **Step 6: Commit containers and tool roadmap**

Run:

```bash
git add personal-wiki/global personal-wiki/domains/.gitkeep personal-wiki/tools/README.md
git commit -m "docs: add personal wiki containers and tool roadmap"
```

Expected: commit succeeds with only the global containers, domain keep file,
and tools README.

## Task 5: Final Phase 1 Verification

**Files:**
- No new files.
- Verify all files created in Tasks 1-4.

- [ ] **Step 1: Run scaffold tests**

Run:

```bash
python -m pytest personal-wiki/tests/test_scaffold.py -q
```

Expected: PASS with all tests passing.

- [ ] **Step 2: Check for unfinished markers**

Run:

```bash
rg -n "TBD|TODO|FIXME|REPLACE_ME" personal-wiki
```

Expected: no output and exit code 1.

- [ ] **Step 3: Check git diff whitespace**

Run:

```bash
git diff --check
```

Expected: no output and exit code 0.

- [ ] **Step 4: Inspect status**

Run:

```bash
git status --short
```

Expected: no uncommitted files under `personal-wiki/`. Existing unrelated
workspace changes outside `personal-wiki/` may remain and must not be reverted.

- [ ] **Step 5: Report completion**

Summarize:

- Test command and result.
- The commits created.
- Any unrelated pre-existing dirty worktree entries left untouched.

Do not claim Phase 2 or later functionality exists.
