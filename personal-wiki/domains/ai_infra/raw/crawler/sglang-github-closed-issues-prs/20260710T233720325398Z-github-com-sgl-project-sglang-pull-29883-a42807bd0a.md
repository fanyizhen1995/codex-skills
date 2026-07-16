---
source_id: sglang-github-closed-issues-prs
title: '[BUG] fix strip streaming empty-string suffix from DSV4 tool arguments'
canonical_url: https://github.com/sgl-project/sglang/pull/29883
captured_at: '2026-07-10T23:37:20.325398+00:00'
content_hash: a42807bd0aef22bc8c820a4dcb350535698341248f70540396ebb555c211bef3
---
# [BUG] fix strip streaming empty-string suffix from DSV4 tool arguments

URL: https://github.com/sgl-project/sglang/pull/29883
State: closed
Labels: 
Closed at: 2026-07-10T09:05:27Z
Merged at: 2026-07-10T09:05:27Z

## Motivation
`_check_for_unstreamed_tool_args` compares the full parsed tool arguments with the arguments that have already been streamed, then sends any remaining suffix at generation finish.

The previous logic always applied `json.dumps()` to the detector's stored `arguments`. This is correct when `arguments` is a Python dict, but some detectors, such as the DeepSeek DSML parser used by DeepSeek v32/v4, store arguments as raw JSON strings. Applying `json.dumps()` again double-encodes those raw strings.

For example, raw arguments `"{}"` became `"\"{}\""`, and the suffix logic could append `\"\"` after `{}`.

Fixes an issue where streamed OpenAI tool call arguments could receive an extra encoded suffix such as `\"\"`, producing invalid arguments like `{}\"\"`.

## Modifications

- Treat string `arguments` as already-serialized raw argument text.
- Keep the existing `json.dumps(..., ensure_ascii=False)` path for dict arguments.
- Compute the remaining suffix only when the already-streamed arguments are a prefix of the expected arguments.
- Add unit tests for raw string tool argument completion behavior.

## Tests

- Added unit coverage for raw JSON string arguments that are already fully
  streamed.
- Added unit coverage for raw JSON string arguments that still require a
  suffix at finish.
- Ran:
  `python3 -m py_compile python/sglang/srt/entrypoints/openai/serving_chat.py test/registered/unit/entrypoints/openai/test_serving_chat.py`







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28561950521](https://github.com/sgl-project/sglang/actions/runs/28561950521)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28561950427](https://github.com/sgl-project/sglang/actions/runs/28561950427)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
