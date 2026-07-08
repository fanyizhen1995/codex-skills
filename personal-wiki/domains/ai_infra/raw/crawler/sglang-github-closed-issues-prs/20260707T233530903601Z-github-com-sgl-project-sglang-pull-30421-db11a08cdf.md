---
source_id: sglang-github-closed-issues-prs
title: '[sglang-miles] Fix stale _attn_sink_local cache after RL weight updates'
canonical_url: https://github.com/sgl-project/sglang/pull/30421
captured_at: '2026-07-07T23:35:30.903601+00:00'
content_hash: db11a08cdf36bc39d12cb111575fe3c3138aad61b8a3ee13a67c5a843b83a6b8
---
# [sglang-miles] Fix stale _attn_sink_local cache after RL weight updates

URL: https://github.com/sgl-project/sglang/pull/30421
State: closed
Labels: deepseek
Closed at: 2026-07-07T20:34:34Z
Merged at: 2026-07-07T20:34:34Z

Cherry-pick of #29916 onto `sglang-miles`.

Fixes the stale `_attn_sink_local` per-rank attention-sink cache (`attn_tp_size > 1`) not being refreshed on RL weight updates, so attention kernels read current weights instead of stale checkpoint values.

Changes vs upstream #29916:
- `self.padded_num_heads` computed once in `MQALayer.__init__`; `refresh_attn_sink_cache()` rebuilds/updates the per-rank padded sink copy, called from `post_load_weights` (base + NextN).
- Lazy per-forward cache build removed → `assert self._attn_sink_local is not None`.
- Conflict resolution: kept sglang-miles's non-gfx942 `x.new_empty` path (this branch predates upstream's gfx942 zero-init and has no `_is_gfx942_supported`); only swapped the local `padded_num_heads` recompute for `self.padded_num_heads`.

Upstream PR: sgl-project/sglang#29916











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28891849536](https://github.com/sgl-project/sglang/actions/runs/28891849536)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28891849231](https://github.com/sgl-project/sglang/actions/runs/28891849231)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
