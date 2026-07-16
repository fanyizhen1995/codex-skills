---
source_id: sglang-github-closed-issues-prs
title: Remove legacy Sphinx docs/ and finish the Mintlify cutover
canonical_url: https://github.com/sgl-project/sglang/pull/28964
captured_at: '2026-07-13T23:40:05.163069+00:00'
content_hash: 868b0e42abea7ec485944d3a1208fa8a730ecd63f6c1858e1fe82431b61da717
---
# Remove legacy Sphinx docs/ and finish the Mintlify cutover

URL: https://github.com/sgl-project/sglang/pull/28964
State: closed
Labels: documentation, quant, amd, dependencies, lora, Multi-modal, deepseek, speculative-decoding, hicache, npu, diffusion, mthreads, apple-silicon
Closed at: 2026-07-13T22:06:09Z
Merged at: 2026-07-13T22:06:09Z

## Summary

The docs have been migrated to `docs_new/` (Mintlify, canonical at docs.sglang.io) and the Sphinx build/deploy workflows are already removed. This completes **Phase 6** of `docs_new/docs_migration_plan.md`: delete the legacy `docs/` tree, clean up everything that pointed at it, and set up link-checking for `docs_new/`.

## What's in it (3 layered commits)

1. **Remove legacy Sphinx `docs/` and repoint references** — delete the 174-file `docs/` tree; repoint source-code docstrings (to in-repo `docs_new/docs/...mdx` paths), `multimodal_gen`/ComfyUI/`benchmark/mmmu` READMEs (to docs.sglang.io), and `.claude` skills; fix the `release-branch-cut` workflow + `scripts/release/README.md` to bump version refs in the `docs_new` install/AMD pages.
2. **docs_new: drop migration leftovers and fix internal links** — remove 14 `.ipynb` + 4 `.rst` Sphinx leftovers (all have `.mdx` twins, none in nav), the finished migration plan, and a stray `intro copy.mdx`; fix all 36 broken internal links/anchors (`mint broken-links` now reports **zero**); refresh the `docs_new` README contribution guide.
3. **ci: gate docs_new links; drop legacy docs/ CI** — Mintlify broken-links PR gate (pinned `mint@4.2.559`), nightly lychee repointed to `docs_new` external links, opt-in manual-stage mint pre-commit hook, ruff now lints `docs_new/` Python, and the now-obsolete `check-no-docs-changes` legacy guard removed.

## Link-checking after this PR

| Where | Tool | Scope |
|---|---|---|
| PR CI (blocking) | `mint broken-links --check-anchors --check-redirects` | docs_new internal links / anchors / redirects |
| Nightly | lychee (`scheme=http/https`) | `README.md` + docs_new external links |
| pre-commit | mint hook (opt-in, manual stage) | local self-check, no forced install |

## Notes

- `mint` is pinned to `4.2.559` (heading-slug rules are version-sensitive) — bump deliberately after re-verifying.
- Out of scope (separate GitHub admin steps): archiving the standalone `sgl-project/sgl-docs` repo.

🤖 Generated with [Claude Code](https://claude.com/claude-code)















































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29284861194](https://github.com/sgl-project/sglang/actions/runs/29284861194)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29284860904](https://github.com/sgl-project/sglang/actions/runs/29284860904)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
