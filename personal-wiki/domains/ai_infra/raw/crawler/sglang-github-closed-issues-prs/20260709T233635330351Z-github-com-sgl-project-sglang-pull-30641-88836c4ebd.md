---
source_id: sglang-github-closed-issues-prs
title: Allow EPLB manual test to use FlashInfer A2A
canonical_url: https://github.com/sgl-project/sglang/pull/30641
captured_at: '2026-07-09T23:36:35.330351+00:00'
content_hash: 88836c4ebdfbbb19f1b9f0080d9c88195bb542a54ae279f2586cb0fe5e804c63
---
# Allow EPLB manual test to use FlashInfer A2A

URL: https://github.com/sgl-project/sglang/pull/30641
State: closed
Labels: run-ci
Closed at: 2026-07-09T10:46:08Z
Merged at: 2026-07-09T10:46:08Z

## Summary

- Let manual EPLB tests select the MoE A2A backend through `SGLANG_EPLB_TEST_MOE_A2A_BACKEND`.
- Add FlashInfer A2A configuration for both server launch args and Engine kwargs.
- Use distinct ports and short shutdown waits for the static EPLB restart flow.

## Testing

- `with-proxy uv run pre-commit run --files test/manual/ep/test_eplb.py`
- `python3 -m py_compile test/manual/ep/test_eplb.py`

## Original commits

- `aa010a046`







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29009955004](https://github.com/sgl-project/sglang/actions/runs/29009955004)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29009954716](https://github.com/sgl-project/sglang/actions/runs/29009954716)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
