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
