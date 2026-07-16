---
source_id: sglang-github-closed-issues-prs
title: 'docs: add VLA card image to cookbook overview'
canonical_url: https://github.com/sgl-project/sglang/pull/31132
captured_at: '2026-07-14T23:40:21.682053+00:00'
content_hash: c0c8e88d6b963db4638f8d0298e8ede8a2107f3abe8aed026b50243f511b8e09
---
# docs: add VLA card image to cookbook overview

URL: https://github.com/sgl-project/sglang/pull/31132
State: closed
Labels: documentation
Closed at: 2026-07-14T07:08:50Z
Merged at: 2026-07-14T07:08:50Z

## Motivation

On the [cookbook overview page](https://docs.sglang.ai/cookbook/intro), the Autoregressive and Diffusion guide cards have cover images, but the VLA (Vision-Language-Action) card renders without one.

## Modifications

- Add `docs_new/cards/VLA-card.png` (940×525 rounded-corner PNG), generated in the same style as the existing `Autoregressive-card.png` / `Diffusion-card.png` (grainy blurred gradient background, bold white centered title).
- Reference it from the VLA card in `docs_new/cookbook/intro.mdx`.

`mint validate` passes.

## Checklist

- [x] Format your code with `pre-commit run --all-files`

🤖 Generated with [Claude Code](https://claude.com/claude-code)







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29313238723](https://github.com/sgl-project/sglang/actions/runs/29313238723)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29313238262](https://github.com/sgl-project/sglang/actions/runs/29313238262)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
