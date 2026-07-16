---
source_id: sglang-github-closed-issues-prs
title: Update GLM-5.2 NVFP4 cookbook
canonical_url: https://github.com/sgl-project/sglang/pull/30826
captured_at: '2026-07-10T23:37:20.318766+00:00'
content_hash: fd06a13f3600df4508892b81d5028a9834ac4e7bde57d8926821b14d2723839b
---
# Update GLM-5.2 NVFP4 cookbook

URL: https://github.com/sgl-project/sglang/pull/30826
State: closed
Labels: documentation
Closed at: 2026-07-10T22:56:33Z
Merged at: 2026-07-10T22:56:33Z

## Summary

- Remove retired `dev-glm52-nvfp4` Docker-image references and NVFP4 benchmark version metadata.
- Apply the low-latency KV cache, CuTeDSL GEMM, request, CUDA graph, and prefill limits only to B300/GB300 NVFP4 recipes.
- Update CP guidance to use `--enable-prefill-cp --cp-strategy interleave` without the Hopper-only caveat.

## Why

The NVFP4 preview image is no longer needed, and the B300/GB300 low-latency tuning belongs only to the NVFP4 checkpoint recipes.

## Validation

- Parsed the GLM-5.2 config and benchmark JSX modules.
- Verified the added low-latency flags are restricted to B300/GB300 NVFP4 cells.
- Confirmed retired image references are absent and rendered the cookbook with `mint dev`.
- Ran `git diff --check` and repository commit hooks.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29128035666](https://github.com/sgl-project/sglang/actions/runs/29128035666)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29128035576](https://github.com/sgl-project/sglang/actions/runs/29128035576)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
