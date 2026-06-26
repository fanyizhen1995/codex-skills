# Compute Accelerators Data Catalog

This directory stores structured, source-backed accelerator specifications for
the `ai_infra` personal-wiki domain.

`raw/` remains the evidence layer, `data/compute_accelerators/` is the
normalized facts layer, and `wiki/` is the curated explanatory layer.

## Layout

- `schema/`: source ranks, accelerator scopes, and field definitions.
- `sources/`: source registry entries shared by observations and crawler
  profiles.
- `skus/`: representative accelerator card, module, chip, and cloud offering
  records.
- `observations/`: source-backed field observations.
- `resolved/`: accepted values that point back to observations.
- `candidates/`: extractor output waiting for review or resolution.

## Update Policy

- Preserve field-level provenance for important parameters.
- Add a new observation when a source changes; do not overwrite evidence.
- Use resolved values only when a source rank policy allows resolution.
- Keep cloud offering aggregate fields separate from single-card fields.
- Keep runtime probe fields separate from official theoretical specs.
- Do not auto-resolve S5 sources unless a reviewer is recorded.

## Validation

Run the structured catalog validator:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators
```

Run the normal wiki validator after curated page edits:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra
```
