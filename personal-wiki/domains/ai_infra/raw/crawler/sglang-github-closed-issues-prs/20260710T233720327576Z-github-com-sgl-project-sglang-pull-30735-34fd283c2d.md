---
source_id: sglang-github-closed-issues-prs
title: 'fix(image-api): return one data item per image for url format with n>1'
canonical_url: https://github.com/sgl-project/sglang/pull/30735
captured_at: '2026-07-10T23:37:20.327576+00:00'
content_hash: 34fd283c2df47f7529b74faba38e88bb8be43a6a5281d93f1f06a5dd74c6a412
---
# fix(image-api): return one data item per image for url format with n>1

URL: https://github.com/sgl-project/sglang/pull/30735
State: closed
Labels: diffusion
Closed at: 2026-07-10T06:32:02Z
Merged at: 

Fixes #30648.

url-format image responses were single-image end to end: only `save_file_path_list[0]` was uploaded/stored, `download_image_content` accepted a `variant` query param but ignored it, and the response builder emitted one `data` item. `b64_json` already returns one per image, so `n>1` was inconsistent.

This stores the n paths/urls per `request_id`, resolves `?variant=N` in the content endpoint, and loops the builder + cloud upload. variant 0 keeps the bare `/content` URL so single-image behavior is unchanged (per the discussion in the issue).

Verified the new logic in isolation — importing the full module clashes with another package in my local env, so I exec'd the two changed functions against stubs:
- `download_image_content`: variant0→path0, variant1→path1, out-of-range→404, legacy item (no `file_paths`)→path0, cloud variant→400 pointing at the right url
- builder url branch: n=2 → 2 data items (`/content`, `/content?variant=1`); cloud → one item per url; no storage → 400

Added `test/unit/test_image_variants.py` for the content-endpoint path (runs in CI).







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29067197612](https://github.com/sgl-project/sglang/actions/runs/29067197612)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29067197583](https://github.com/sgl-project/sglang/actions/runs/29067197583)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
