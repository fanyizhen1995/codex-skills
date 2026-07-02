---
source_id: sglang-github-closed-issues-prs
title: 'feat: extend weight checker to speculative draft worker(s)'
canonical_url: https://github.com/sgl-project/sglang/pull/27750
captured_at: '2026-07-01T02:12:08.953963+00:00'
content_hash: 7b6aaa99201f48eb6926b0a32bab11397e7a18a59a6b06a9cb15c591fe498b7c
---
# feat: extend weight checker to speculative draft worker(s)

URL: https://github.com/sgl-project/sglang/pull/27750
State: closed
Labels: 
Closed at: 2026-06-30T22:05:01Z
Merged at: 2026-06-30T22:05:01Z

## Summary

Extend the weight checker to speculative draft worker(s) and add tensor-name skipping.

## Motivation

`check_weights` reached the draft model through an ad-hoc single-draft helper and could not skip tensors a job never updates. RL / weight-sync runs with speculative draft worker(s) must checksum and compare draft weights too, and an LLM-only RL job must skip the vision tower it never touches.

## Usage

```python
CheckWeightsReqInput(action="checksum", selector="all", skip_tensor_list=["visual."])
```

`selector` is `target` / `draft` / `all` (default `all`). Checksum keys return role-namespaced: target unprefixed, draft under `draft.` / `draft_step_<i>.`; `parallelism_info` carries one entry per role.

## Design Notes

- **Routing:** `check_weights` fans out over `get_model_runners(selector)` for every draft runner.
- **Collision:** `_merge_checksum_payloads` raises on a duplicate role-prefixed key.
- **Shape change:** `parallelism_info` becomes a list of per-role dicts.
- **Skip parity:** `_is_skip_weight_check` makes `reset_tensors` poison exactly what `compare` verifies.

## Verification

- **Tests added:** `TestSkipTensorList` asserts `reset` / `compare` / `checksum` honor `skip_tensor_list` identically.
- **Updated:** `test_e_checksum_returns_ranks_with_hashes` covers the per-role `parallelism_info` list.

## Review Focus

- Scrutinize `_merge_checksum_payloads` collision handling for role-prefixed keys.
- Scrutinize the `parallelism_info` dict-to-list change against downstream checksum consumers.
- Scrutinize reset / compare skip-scope parity through `_is_skip_weight_check`.

























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28472966875](https://github.com/sgl-project/sglang/actions/runs/28472966875)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28472966734](https://github.com/sgl-project/sglang/actions/runs/28472966734)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
