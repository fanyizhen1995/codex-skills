---
source_id: sglang-github-closed-issues-prs
title: Fix async generator reader lock leak causing pause_generation to hang
canonical_url: https://github.com/sgl-project/sglang/pull/29324
captured_at: '2026-07-04T02:13:49.130312+00:00'
content_hash: ad3accd29c577a6fcb9f7a190501a95bc7f3f2c58a3fe0731c80fcc3f8c07183
---
# Fix async generator reader lock leak causing pause_generation to hang

URL: https://github.com/sgl-project/sglang/pull/29324
State: closed
Labels: documentation
Closed at: 2026-06-25T19:31:27Z
Merged at: 

## Summary
- Multiple HTTP endpoint handlers called `generate_request().__anext__()` without closing the async generator, permanently leaking the `model_update_lock` reader lock
- This caused `pause_generation("abort")` to spin forever waiting for the reader count to reach 0, hanging `test_update_weights_from_tensor.py`
- Fix: wrap every `__anext__()` call with `try/finally: await gen.aclose()` across 10 files, and fix the health check to not interrupt generator cleanup via task cancellation

## Test plan
- [x] All 5 tests in `test/registered/rl/test_update_weights_from_tensor.py` pass (~250s)
- See `report.md` for full debugging notes





<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28195347355](https://github.com/sgl-project/sglang/actions/runs/28195347355)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28195347208](https://github.com/sgl-project/sglang/actions/runs/28195347208)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
