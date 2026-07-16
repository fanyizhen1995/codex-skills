---
source_id: sglang-github-closed-issues-prs
title: Fix gate stride for 4D decode layouts
canonical_url: https://github.com/sgl-project/sglang/pull/31231
captured_at: '2026-07-15T23:40:28.383397+00:00'
content_hash: d7d12929f27b11beb9007db92b7c68333cb2201452d5c970ea00cdf67698c3e3
---
# Fix gate stride for 4D decode layouts

URL: https://github.com/sgl-project/sglang/pull/31231
State: closed
Labels: run-ci
Closed at: 2026-07-15T03:06:51Z
Merged at: 2026-07-15T03:06:50Z

## Summary

- Use the token-axis stride for 4D gate tensors in the fused sigmoid gating recurrent update.
- Preserve the existing stride behavior for 2D and 3D layouts.

## Testing

- `python3 -m py_compile python/sglang/srt/layers/attention/fla/fused_sigmoid_gating_recurrent.py`
- `git diff --check`
- `git ls-files --eol -- python/sglang/srt/layers/attention/fla/fused_sigmoid_gating_recurrent.py`
- Not run locally: `uv run pre-commit run --files ...` and `uv run ruff check ...` because those commands were not installed in the local uv environment.

## Original commits

- `3b43dcb9b`







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29373243349](https://github.com/sgl-project/sglang/actions/runs/29373243349)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29373243071](https://github.com/sgl-project/sglang/actions/runs/29373243071)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
