---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] Enable SANA-WM consistency check'
canonical_url: https://github.com/sgl-project/sglang/pull/27560
captured_at: '2026-07-05T02:14:10.256905+00:00'
content_hash: b9d164900c7874bf0d55efaaa4bfe52274825faa77720ced170f0b4e095aa42d
---
# [diffusion] Enable SANA-WM consistency check

URL: https://github.com/sgl-project/sglang/pull/27560
State: closed
Labels: run-ci, diffusion, jit-kernel
Closed at: 2026-07-04T07:26:24Z
Merged at: 

## Summary

- keep the SANA-WM TI2V CI case on the consistency path explicitly
- keep using the current main ci-data revision, which already contains the same SANA-WM GT frames
- include the small explicit pipeline config guard suggested in review

## ci-data

Current main already pins `SGL_TEST_FILES_CI_DATA_REVISION` to `caa56302ccf2d289e4488ed06d952edf5d2314cf`, and that revision contains:

- `sana_wm_ti2v_1gpu_frame_0.png`
- `sana_wm_ti2v_1gpu_frame_mid.png`
- `sana_wm_ti2v_1gpu_frame_last.png`

The earlier sibling ci-data commit `11256832ef94701c5d535e630ce848651731ab70` contains byte-identical SANA-WM GT frames, so this PR no longer changes the global ci-data pin.

## Validation

Pending CI.























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28037899208](https://github.com/sgl-project/sglang/actions/runs/28037899208)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28037898277](https://github.com/sgl-project/sglang/actions/runs/28037898277)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
