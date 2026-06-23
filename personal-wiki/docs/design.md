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
