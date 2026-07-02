---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] warmup: default to model sampling resolution (declare Z-Image
  default)'
canonical_url: https://github.com/sgl-project/sglang/pull/29519
captured_at: '2026-07-01T02:12:08.968473+00:00'
content_hash: 437b1b671c616f5b4198e3b70a60cbdfd26981f4ef45872894797c2e9fcfafed
---
# [diffusion] warmup: default to model sampling resolution (declare Z-Image default)

URL: https://github.com/sgl-project/sglang/pull/29519
State: closed
Labels: run-ci, diffusion
Closed at: 2026-06-30T02:32:12Z
Merged at: 2026-06-30T02:32:12Z

## Motivation

Server-based image warmup defaulted to an **area-capped "representative" resolution** (`SERVER_WARMUP_IMAGE_MAX_AREA` = 768×768). For larger real requests (e.g. 1024×1024) the first request still paid first-shape kernel autotuning — a ~0.1s residual measured on H100, even though warmup *ran*.

## Fix

`_resolve_default_warmup_resolution`: for **image** warmup, prefer the model's `sampling_defaults` width/height (the most likely real request shape) instead of the area-capped representative, so kernels are specialized for the actual shape. **Video keeps the area/frame caps** (a full-resolution video warmup is far costlier). Representative selection remains the fallback when a model declares no default width/height.

Z-Image declared no default resolution (it accepts arbitrary /16 resolutions, so `width/height` were left `None`), and therefore fell back to the cap. Declare its **official default 1024×1024** (`supported_resolutions` stays `None` = all allowed, so other resolutions still work without spurious warnings).

## Verification (H100)

`serve --warmup` with **no explicit `--warmup-resolutions`** now warms at the model default and matches the client-side-warmup baseline:

| case | before (area cap) | after (model default) | baseline |
|---|---|---|---|
| FLUX.1-dev | 4.80s (warm @ ≤768²) | **4.70s** (warm @ 1024) | 4.68 |
| Ideogram-4 | 5.26s | **5.21s** (warm @ 1024) | 5.19 |
| Z-Image-Turbo | 512 fallback | **warms @ 1024** | 0.65 |

## Relationship

Complements the `--warmup` dead-zone fix (so server-based warmup actually runs) — that fix is tracked separately. This PR is purely about *which resolution* the default warmup uses.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

















































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28390506011](https://github.com/sgl-project/sglang/actions/runs/28390506011)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28390505790](https://github.com/sgl-project/sglang/actions/runs/28390505790)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
