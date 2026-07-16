---
source_id: sglang-github-closed-issues-prs
title: Fix MiMo audio FA3 import laziness
canonical_url: https://github.com/sgl-project/sglang/pull/31374
captured_at: '2026-07-15T23:40:28.351408+00:00'
content_hash: 73c2afecf89fdb3d86e1d8a2b1618a6073688bdf9ffc2af8b94003ceba1b6537
---
# Fix MiMo audio FA3 import laziness

URL: https://github.com/sgl-project/sglang/pull/31374
State: closed
Labels: run-ci
Closed at: 2026-07-15T22:35:40Z
Merged at: 

## Summary
- Lazy-load `sgl_kernel.flash_attn` from MiMo audio attention instead of importing FA3 at module import time.
- Allows `sglang.srt.models.mimo_v2` to import when the installed `sglang-kernel` wheel does not ship `flash_ops`.

## Test
- `uv run python3 -c "import sglang.srt.models.mimo_v2"`



<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->_Not run yet_<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:warning: **Not enabled** -- add `run-ci-extra` label to opt in.<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
