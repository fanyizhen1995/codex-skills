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

Local CLI tools are available through:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki <command>
```

See `docs/cli.md` for command examples.

The project-local Codex skill lives at
`skills/personal-wiki-manager/SKILL.md`. It routes query, ingest, validate,
refactor, create-domain, and image-note work while enforcing the repository
read protocol.

Agents must read `WIKI.md` before maintaining this repository.
