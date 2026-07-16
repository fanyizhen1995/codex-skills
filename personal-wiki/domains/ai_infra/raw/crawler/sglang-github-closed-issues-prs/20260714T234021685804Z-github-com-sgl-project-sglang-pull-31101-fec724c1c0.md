---
source_id: sglang-github-closed-issues-prs
title: Fix diffusion cookbook overview cards
canonical_url: https://github.com/sgl-project/sglang/pull/31101
captured_at: '2026-07-14T23:40:21.685804+00:00'
content_hash: fec724c1c02545e975df06918869657b3123a05ea3b931097c0a3c4c3a00d73c
---
# Fix diffusion cookbook overview cards

URL: https://github.com/sgl-project/sglang/pull/31101
State: closed
Labels: documentation
Closed at: 2026-07-14T02:40:43Z
Merged at: 2026-07-14T02:40:43Z

## Summary
- Add the missing LongLive 2.0 card to the diffusion cookbook overview
- Rename the JoyEcho display label to the official JoyAI-Echo name
- Replace the JoyAI-Echo overview card logo so it no longer reuses the LTX logo

## Test Plan
- pre-commit run --files docs_new/cookbook/diffusion/intro.mdx docs_new/cookbook/diffusion/JoyEcho/JoyEcho.mdx docs_new/docs.json docs_new/cards/logos/joyai-echo.svg







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29301027388](https://github.com/sgl-project/sglang/actions/runs/29301027388)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29301027232](https://github.com/sgl-project/sglang/actions/runs/29301027232)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
