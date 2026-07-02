---
source_id: sglang-github-closed-issues-prs
title: '[sglang-miles] Fix post_process_weights deadlock in RL in-place mode'
canonical_url: https://github.com/sgl-project/sglang/pull/29670
captured_at: '2026-07-01T02:12:08.975388+00:00'
content_hash: 33abdf29aa4afc95d1faea2ff0b674ac7c2afbb92249fcec5495069cb236f99a
---
# [sglang-miles] Fix post_process_weights deadlock in RL in-place mode

URL: https://github.com/sgl-project/sglang/pull/29670
State: closed
Labels: 
Closed at: 2026-06-29T19:40:41Z
Merged at: 2026-06-29T19:40:41Z

## Summary

Restore the pause-aware locking behavior for `post_process_weights` on the `sglang-miles-v0.5.13` branch.

This is the `post_process_weights` hunk from the earlier pause-aware deadlock fix in https://github.com/sgl-project/sglang/pull/22754, which appears to have been lost during the v0.5.13 `tokenizer_control_mixin.py` refactor.

`sglang-miles-v0.5.12` skipped `model_update_lock.writer_lock` when the engine was already paused. During the v0.5.13 refactor to `tokenizer_control_mixin.py`, `post_process_weights` became an unconditional writer-lock acquisition. That can deadlock with `pause_generation(mode="in_place")`:

```text
active /generate holds model_update_lock.reader_lock
pause_generation(in_place) preserves the request and pauses progress
post_process_weights waits for writer_lock
continue_generation is only called after post_process_weights
```

The result is that health generation stops making progress and post-load processing can time out.

## Fix

- Check `self.is_pause` under `is_pause_cond`.
- Use `model_update_lock.writer_lock` only when the engine is not paused.
- Use `nullcontext()` while paused, matching the pause-aware behavior from the earlier miles branch.

## Validation

```bash
python3 -m py_compile python/sglang/srt/managers/tokenizer_control_mixin.py
```























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28393955205](https://github.com/sgl-project/sglang/actions/runs/28393955205)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28393954957](https://github.com/sgl-project/sglang/actions/runs/28393954957)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
