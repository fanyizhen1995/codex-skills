---
source_id: sglang-github-closed-issues-prs
title: 'fix: pin flash-attn-4 to 4.0.0b16'
canonical_url: https://github.com/sgl-project/sglang/pull/31278
captured_at: '2026-07-15T23:40:28.380131+00:00'
content_hash: 9062a4e6d7d8284e00436e2152f21d1e78d872880bab0d9dba3d686a64cda626
---
# fix: pin flash-attn-4 to 4.0.0b16

URL: https://github.com/sgl-project/sglang/pull/31278
State: closed
Labels: dependencies
Closed at: 2026-07-15T04:48:02Z
Merged at: 

## Summary
Pin the Python package dependency on FlashAttention 4 beta 16.

## Symptom & Reproduction
- **Symptom:** Python package installations select `flash-attn-4==4.0.0b15` instead of `4.0.0b16`.
- **Reproduction:** Run `rg -n 'flash-attn-4' python/pyproject.toml` on `main`.

## Root Cause
1. `python/pyproject.toml` pins `flash-attn-4` to `4.0.0b15`.
2. `project.dependencies` therefore resolves the previous beta release.

## Fix
Update the existing exact dependency pin to `flash-attn-4==4.0.0b16`.

## Verification
- **New / updated test:** A `tomllib` assertion confirms the exact dependency value in `python/pyproject.toml`.

## Review Focus
- Scrutinize the `flash-attn-4` version in `python/pyproject.toml`.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29389757149](https://github.com/sgl-project/sglang/actions/runs/29389757149)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29389757028](https://github.com/sgl-project/sglang/actions/runs/29389757028)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
