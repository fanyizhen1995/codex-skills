# Personal Wiki CLI

Run the CLI by script path because `personal-wiki` contains a hyphen:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki <command>
```

If `--root` is omitted, the CLI tries to infer the repository root from the current directory.

## init-domain

Create a domain scaffold with raw folders, wiki folders, `DOMAIN.md`, `ingest.md`, and `wiki/index.md`.

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki init-domain ai-infra
```

## validate

Validate wiki frontmatter, accepted `type` and `status` values, local `source_refs`, Markdown links, image paths, duplicate titles and aliases, and reviewed pages without sources.

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai-infra
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai-infra --json
```

## index

Regenerate a domain `wiki/index.md` from page frontmatter.

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki index ai-infra
```

## backlinks

Print backlinks as JSON for global wiki pages or one domain. Use `--write-json` to write `backlinks.json` into the selected wiki root.

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki backlinks
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki backlinks --domain ai-infra
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki backlinks --domain ai-infra --write-json
```

## graph

Write a graph JSON file containing nodes and edges for global wiki pages or one domain.

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki graph --out graph.json
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki graph --domain ai-infra --out ai-infra-graph.json
```

## visualize

Write a static HTML graph visualization with embedded data and no external assets.

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki visualize --out graph.html
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki visualize --domain ai-infra --out ai-infra-graph.html
```

## snapshot-url

Create a raw web source under `domains/<domain>/raw/links/`. Without `--fetch`, the file records the URL and capture metadata only. With `--fetch`, the command stores fetched page text when available.

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki snapshot-url ai-infra https://example.com/article
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki snapshot-url ai-infra https://example.com/article --fetch
```

## image-note

Create a draft Reference page for an image source.

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki image-note ai-infra raw/images/diagram.png
```

## ingest-plan

Create an ingest plan next to a raw source and append a pending entry to the domain ingest log.

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki ingest-plan ai-infra raw/links/example-com-article.md
```
