# Personal Wiki Roadmap

This roadmap preserves the complete implementation plan beyond the initial
scaffold.

## Phase 1: Repository specification and templates

Status: Implemented.

Acceptance criteria:

- Root `WIKI.md` exists and defines the LLM read protocol.
- Root `ROADMAP.md` preserves later phases.
- Domain templates exist.
- Wiki page templates exist for Concept, Paper, Project, Decision, and Reference.
- Raw source templates exist.
- Image storage and image reference rules are documented.

## Phase 2: Validation tooling

Status: Implemented.

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

Status: Implemented.

Build:

```text
wiki index <domain>
wiki backlinks [--domain <name>]
wiki graph [--domain <name>] [--out graph.json]
wiki visualize [--domain <name>] [--out graph.html]
```

Acceptance criteria:

- Domain index generation uses page frontmatter.
- Backlink extraction handles relative Markdown links.
- Graph export includes nodes, links, page types, tags, and descriptions.

## Phase 4: Ingest assistance

Status: Implemented.

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

Status: Implemented.

Create a `personal-wiki-manager` Codex skill.

Acceptance criteria:

- The skill routes query, ingest, validate, refactor, create-domain, and
  image-note requests.
- The skill enforces the read protocol in `WIKI.md`.
- The skill respects domain boundaries by default.

## Phase 6: Optional publication and visualization

Status: Implemented for static graph visualization.

Add optional human-facing outputs only after LLM-first workflows are stable.

Acceptance criteria:

- Static graph HTML is generated without external assets.

Implemented output:

- Static graph HTML.

Remaining future ideas:

- MkDocs or Quartz publication.
- Obsidian compatibility notes.
