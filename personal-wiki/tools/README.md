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
