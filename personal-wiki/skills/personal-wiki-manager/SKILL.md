---
name: personal-wiki-manager
description: Use when managing a personal-wiki repository for query, ingest, compact, validate, refactor, create-domain, or image-note requests.
---

# Personal Wiki Manager

## Purpose

Maintain a local, file-first personal wiki. `raw/` is the fact source, `wiki/` is the curated knowledge layer, `domains/` isolates topic areas, and `global/` stores only knowledge reused across multiple domains.

## Read Order

1. Read `WIKI.md`.
2. Read the active domain's `DOMAIN.md` and `ingest.md`.
3. Read relevant raw sources before changing curated wiki pages.
4. Read existing nearby wiki pages before adding or refactoring pages.

## Modes

Mode routing:

- Query: answer from existing raw and wiki files.
- Ingest: turn raw source material into proposed wiki updates.
- Compact: reduce raw storage without changing facts.
- Validate: run checks and report issues.
- Refactor: reorganize existing wiki pages without changing facts.
- Create-Domain: create a new domain scaffold.
- Image-Note: draft a Reference page for an important image.

## Query Mode

Default scope is one domain. Use `global/` only for cross-domain knowledge. Prefer citations to `source_refs` or raw paths when answering factual questions.

## Ingest Mode

Read the raw source first, then draft the smallest useful curated pages. Preserve `source_refs` back to raw material. `ingest-plan` may append a pending `ingest.md` entry immediately; promoting drafted curated wiki changes beyond a pending plan requires user approval.

After durable wiki pages cite large raw sources, compact bulky raw evidence before the final index and validation step. Preserve readable summaries or indexes when they are useful entry points.

## Compact Mode

Compact workflow:

1. Read the domain index, pages that cite the target raw files, and `ingest.md`.
2. Measure raw size before changes.
3. Gzip large raw evidence files and bulky derived page dumps; keep useful `summary` or `index` files readable unless the user asks for maximum compression.
4. Replace originals only after a compressed equivalent exists, and record the mapping in a manifest or ingest log.
5. Update `source_refs`, Markdown links, and ingest-plan/log paths that pointed at renamed raw files.
6. Rebuild index/backlinks when relevant, run validation, then report changed paths and space saved.

## Validate Mode

Run validation before and after changes:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain <name>
```

Use `--json` when structured output is needed.

## Refactor Mode

Keep facts anchored to raw sources. Preserve or update links, backlinks, aliases, and `source_refs`. Do not promote a page to `reviewed` unless the user explicitly approves reviewed promotion.

## Create-Domain Mode

Create one domain at a time:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki init-domain <name>
```

After creation, read the new `DOMAIN.md` and keep future work inside that domain boundary unless the user asks for cross-domain changes.

## Image-Note Mode

Image-note workflow:

1. Confirm the image belongs in the active domain's raw image area or is otherwise a valid source reference.
2. Create a draft image Reference page:
   ```bash
   python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki image-note <domain> <image-path>
   ```
3. Fill in what the image shows, why it matters, and the raw image source.
4. Validate the domain.

## Safety Rules

- `raw/` is the fact source; do not overwrite raw evidence casually.
- Compressed raw remains raw evidence. Do not delete an original unless a `.gz` equivalent or documented rebuild path remains.
- When raw paths change during compaction, update every `source_ref`, Markdown link, and ingest log that names the old path.
- `wiki/` is the curated layer; do not add unsupported claims.
- Default scope is one domain; respect the domain boundary.
- Use `global/` only when knowledge is reused across multiple domains.
- Reviewed promotion needs user approval.
- Prefer proposed ingest plans before applying broad changes.

## Commands

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki init-domain <name>
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate [--domain <name>] [--json]
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki index <domain>
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki backlinks [--domain <name>] [--write-json]
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki graph [--domain <name>] [--out graph.json]
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki visualize [--domain <name>] [--out graph.html]
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki snapshot-url <domain> <url> [--fetch]
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki image-note <domain> <image-path>
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki ingest-plan <domain> <raw-path>
```

There is no dedicated compact CLI command. Use normal shell compression tools
such as `gzip` for large raw files, then run `index`, `backlinks`, and
`validate` from the CLI.
