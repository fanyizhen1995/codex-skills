---
source_id: sglang-github-closed-issues-prs
title: 'fix: apply custom logit processor in SPEC_V2 verification path'
canonical_url: https://github.com/sgl-project/sglang/pull/26334
captured_at: '2026-07-12T23:38:53.055131+00:00'
content_hash: cae01cfccb6005c5d23784db38f37eabb50669f4c203032c432e5bc80a1694d2
---
# fix: apply custom logit processor in SPEC_V2 verification path

URL: https://github.com/sgl-project/sglang/pull/26334
State: closed
Labels: 
Closed at: 2026-05-26T02:15:06Z
Merged at: 

## Problem

The SPEC_V2 verification path (`eagle_info_v2.py`) was missing the call to `apply_custom_logit_processor()` in the `sample()` method, causing custom logit processors (e.g., `thinking_budget` for Qwen3.5 reasoning models) to be completely bypassed when speculative decoding is enabled.

## Root cause

V1 implementations (`eagle_info.py`, `ngram_info.py`) correctly call `apply_custom_logit_processor()` before applying penalties, but V2 (`eagle_info_v2.py`) skipped this step entirely — meaning `ThinkingBudgetLogitProcessor` and other custom processors never executed during speculative decoding verification.

## Fix

Added the missing `apply_custom_logit_processor()` call in `EagleVerifyInputV2.sample()`, aligned with V1 implementation:

- `eagle_info.py` (V1): L290-295
- `ngram_info.py` (V1): L408-413
- `dflash_info.py`: L344-347

## Testing

Tested with Qwen3.5 + NEXTN speculative decoding + `thinking_budget=1200`:

| Before fix | After fix |
|---|---|
| reasoning_tokens: 3245 | reasoning_tokens: 1211 |
| budget not enforced | budget enforced (~1200) |

> Note: This PR was created via vibe coding based on local testing. The fix follows the exact same pattern as existing V1 implementations.

Fixes #26330
Related to #21724







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #26428239861](https://github.com/sgl-project/sglang/actions/runs/26428239861)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #26428239723](https://github.com/sgl-project/sglang/actions/runs/26428239723)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
