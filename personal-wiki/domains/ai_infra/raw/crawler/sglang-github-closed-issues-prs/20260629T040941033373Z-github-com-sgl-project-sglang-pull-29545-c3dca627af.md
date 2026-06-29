---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] CI: make consistency GT probe robust to transient CDN failures'
canonical_url: https://github.com/sgl-project/sglang/pull/29545
captured_at: '2026-06-29T04:09:41.033373+00:00'
content_hash: c3dca627afceb73bba5da4f7463844bb651c46174f4f92aa93a79dab36e6b686
---
# [diffusion] CI: make consistency GT probe robust to transient CDN failures

URL: https://github.com/sgl-project/sglang/pull/29545
State: closed
Labels: run-ci, diffusion
Closed at: 2026-06-28T09:13:54Z
Merged at: 2026-06-28T09:13:54Z

## Problem

The diffusion consistency check's `_remote_file_exists` (in `multimodal_gen/test/test_utils.py`) can report a **present** GT as missing whenever `raw.githubusercontent.com` momentarily fails, surfacing as a misleading CI failure:

```
[consistency] GT not found for <case>. See logs for instructions to add GT.
```

…even though the GT file exists in `sgl-project/ci-data` at the pinned revision. Consistency failures are classified **non-retryable**, so the in-job retry framework does not cover this — the job goes red and needs a manual workflow re-run.

## Evidence (NV CUDA, not AMD/NPU)

- `mova_360p_ring1_uly2`, `cosmos3_nano_t2i` and `wan2_2_t2v_a14b_lora_2gpu` hit transient "GT not found" while their GT was present at the pinned revision `4a271ef3…` (verified via the contents API and the raw CDN).
- **Smoking gun**: in one 2-gpu job, `wan2_2_t2v_a14b_lora_2gpu` consistency **PASSED earlier in the same job**, then reported "GT not found" later. The GT file is static — so the remote existence probe blipped, not the file.
- Plain workflow re-runs cleared all of these with **no GT added**.

## Root cause

`_remote_file_exists` had two gaps:
1. a tight 3-shot retry loop with **no backoff** → could exhaust during a brief 429 / rate-limit burst;
2. it **trusted a 404 on first sight** → `raw.githubusercontent.com` can serve a transient 404 for a freshly-pinned commit before its CDN edge is warm.

## Fix

Enhance `_remote_file_exists` (keeps the `bool | None` contract that `_find_remote_consistency_gt_files` relies on, where `None` ⇒ "assume present" — introduced in #28762):

- **exponential backoff** between retries (1→16s) to ride out rate-limit / CDN windows;
- **do not trust a 404 on first sight** — absence is believed only if it persists across *all* attempts with no 200/206 in between; a 200/206 on any attempt wins.

Net effect: a momentary CDN/network blip resolves as `True` (found) or `None` (assume present), never a false `False` → no more spurious "GT not found". A genuinely-missing GT (consistently 404 across all attempts) still returns `False` and reports correctly.

## Test

Unit-level state coverage all pass:

| input | result |
|---|---|
| 200 | `True` |
| HEAD 405 → GET 206 | `True` |
| persistent 404 | `False` (genuinely missing) |
| **pseudo-404 then 200** (CDN warm) | `True` ✅ (previously `False`) |
| persistent 429 | `None` (assume present) |
| 429 burst then 200 | `True` |
| persistent timeout | `None` |
| persistent 503 | `None` |

🤖 Generated with [Claude Code](https://claude.com/claude-code)







































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28314169558](https://github.com/sgl-project/sglang/actions/runs/28314169558)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28314169506](https://github.com/sgl-project/sglang/actions/runs/28314169506)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
