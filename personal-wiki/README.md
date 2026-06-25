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
`skills/personal-wiki-manager/SKILL.md`. It routes query, ingest, compact,
validate, refactor, create-domain, and image-note work while enforcing the
repository read protocol.

Agents must read `WIKI.md` before maintaining this repository.

## Agent Skill Loading

The skill is kept inside this repository so it can evolve with the wiki:

```text
personal-wiki/skills/personal-wiki-manager/SKILL.md
```

For one-off use, do not install anything. Ask the agent to load the project
skill explicitly:

```text
Read personal-wiki/WIKI.md, then read
personal-wiki/skills/personal-wiki-manager/SKILL.md.
Use personal-wiki-manager for this task.
```

For regular Codex use, install or link the skill into the Codex skills
directory, then restart Codex:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R personal-wiki/skills/personal-wiki-manager \
  "${CODEX_HOME:-$HOME/.codex}/skills/personal-wiki-manager"
```

If you want edits in this repository to be picked up immediately, use a
symbolic link instead of a copy:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -sfn "$(pwd)/personal-wiki/skills/personal-wiki-manager" \
  "${CODEX_HOME:-$HOME/.codex}/skills/personal-wiki-manager"
```

For Claude Code, place or link the same folder under `~/.claude/skills/`:

```bash
mkdir -p "$HOME/.claude/skills"
ln -sfn "$(pwd)/personal-wiki/skills/personal-wiki-manager" \
  "$HOME/.claude/skills/personal-wiki-manager"
```

After installing or linking, restart the agent session so the skill metadata is
discovered.
