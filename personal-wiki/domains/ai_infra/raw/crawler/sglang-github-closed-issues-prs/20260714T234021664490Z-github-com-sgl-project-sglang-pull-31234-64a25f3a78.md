---
source_id: sglang-github-closed-issues-prs
title: 'ci: strip invisible Unicode format chars from slash-command input'
canonical_url: https://github.com/sgl-project/sglang/pull/31234
captured_at: '2026-07-14T23:40:21.664490+00:00'
content_hash: 64a25f3a78710bb66f95e1731663ab7b05d54e72f84f58aeab039c70079e753f
---
# ci: strip invisible Unicode format chars from slash-command input

URL: https://github.com/sgl-project/sglang/pull/31234
State: closed
Labels: 
Closed at: 2026-07-14T23:33:46Z
Merged at: 2026-07-14T23:33:46Z

## Motivation

On #31059, `/rerun-test test_mamba_unittest.py` failed twice with *No test file found matching* even though the file exists. Hexdumping the comments shows the pasted filename ends in `E2 80 8E` — **U+200E LEFT-TO-RIGHT MARK**, invisible in the GitHub UI and typically injected by GitHub's copy-path button or rich-text copy. `str.strip()` removes whitespace only (U+200E is category Cf, not whitespace), so the handler literally searched for `test_mamba_unittest.py‎` and correctly found nothing.

## Modifications

Add `_strip_format_chars()` (drops all Unicode category-Cf characters: LRM/RLM U+200E/200F, zero-width U+200B–200D, word joiner U+2060, BOM U+FEFF) and apply it to `COMMENT_BODY` once at ingestion in `main()`, so every slash command and every argument is covered. Format characters are display hints and never legitimate in a command or path, so dropping them is always safe; non-Cf content (CJK filenames, `::` selectors, flags) passes through unchanged.

Verified against the exact poisoned bytes from #31059, all seven listed format chars, and legitimate-input passthrough.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29374601123](https://github.com/sgl-project/sglang/actions/runs/29374601123)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29374600998](https://github.com/sgl-project/sglang/actions/runs/29374600998)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
