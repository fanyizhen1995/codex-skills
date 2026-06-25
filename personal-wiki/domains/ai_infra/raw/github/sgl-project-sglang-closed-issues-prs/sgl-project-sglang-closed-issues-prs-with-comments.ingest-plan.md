# Ingest Plan

Source path: raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-with-comments.split-manifest.json

## Candidate page types
- Concept
- Paper
- Reference
- Project

## Next steps
- Review the raw source and identify durable claims.
- Choose the smallest appropriate wiki page type for each claim.
- Preserve source_refs back to the raw source.
- Update the ingest log after drafted pages are reviewed.

## Storage note

The original joined gzip corpus is represented by a split manifest and deterministic part files because the single gzip blob exceeds GitHub single-file limits. Use the manifest reassemble command to recreate the original gzip byte-for-byte.
