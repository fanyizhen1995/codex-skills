---
source_id: sglang-github-closed-issues-prs
title: '[codex] Add VLM image DP scheduling research note'
canonical_url: https://github.com/sgl-project/sglang/pull/29728
captured_at: '2026-07-01T02:12:08.960116+00:00'
content_hash: e5af9c0f7cad5f63f4d61fe3d2b532d91fd2795b7b2b8ffa4b5d3e6884f6c64b
---
# [codex] Add VLM image DP scheduling research note

URL: https://github.com/sgl-project/sglang/pull/29728
State: closed
Labels: documentation, Multi-modal
Closed at: 2026-06-30T08:15:30Z
Merged at: 

## Summary

- Adds `docs/developer_guide/vlm_image_dp_scheduling.md` as a PR research note for VLM image-level DP scheduling.
- Captures scheduling semantics, padding/bucket alignment, `segment_id` handling, and all-to-all image embedding refill.
- Includes open review questions and a review checklist.

## Validation

- `python3` doc sanity check confirmed the document has the expected title, mermaid diagram, and review checklist.
- Full Sphinx/MyST build not run because `myst_parser` is not installed in this local environment.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28429017306](https://github.com/sgl-project/sglang/actions/runs/28429017306)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28429017160](https://github.com/sgl-project/sglang/actions/runs/28429017160)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
