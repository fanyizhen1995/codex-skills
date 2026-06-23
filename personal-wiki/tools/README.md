# Tools

This directory contains local tooling for the personal wiki. The CLI is
implemented in `wiki_cli/` and is invoked by script path because
`personal-wiki` contains a hyphen.

Usage:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki <command>
```

See `docs/cli.md` for all commands and examples.

Tooling principles:

- The filesystem remains the source of truth.
- Commands should report validation issues before mutating files.
- Commands should be testable without network access unless they explicitly
  snapshot URLs.
- Tools should work one domain at a time by default.
