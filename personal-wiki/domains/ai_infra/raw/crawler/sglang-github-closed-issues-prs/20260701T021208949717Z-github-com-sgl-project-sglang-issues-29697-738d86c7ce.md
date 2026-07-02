---
source_id: sglang-github-closed-issues-prs
title: '[Apple Silicon] [CI] Fix 3 stale model-free unit tests deselected in pr-test-mlx'
canonical_url: https://github.com/sgl-project/sglang/issues/29697
captured_at: '2026-07-01T02:12:08.949717+00:00'
content_hash: 738d86c7ce3e0f8288bebe493c02d8eb5f5e5295267b889d8284d0a175f86bb1
---
# [Apple Silicon] [CI] Fix 3 stale model-free unit tests deselected in pr-test-mlx

URL: https://github.com/sgl-project/sglang/issues/29697
State: closed
Labels: 
Closed at: 2026-06-30T22:15:08Z
Merged at: 

Deselected by `-k` in `.github/workflows/pr-test-mlx.yml` (PR #29691). Model-free but stale against `main`; only ever skipped on ubuntu, so drift went uncaught:

- `test_decode_finalize_does_not_snapshot_auxiliary_state` : `MlxModelRunner._clear_steps` now set in`__init__`, fake runner omits it.
- `test_mlx_scheduler_init_overlap_keeps_future_map_relay` : `decide_needs_cpu_seq_lens` now reads `server_args.speculative_algorithm`.
- `test_finished_request_snapshots_before_release` : `_handle_finished_req` renamed to `_handle_finish_state_updated_req`.

Each needs a signature fix, then re-enable in the workflow `-k` list.
