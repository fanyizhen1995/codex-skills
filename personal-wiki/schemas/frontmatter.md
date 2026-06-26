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
