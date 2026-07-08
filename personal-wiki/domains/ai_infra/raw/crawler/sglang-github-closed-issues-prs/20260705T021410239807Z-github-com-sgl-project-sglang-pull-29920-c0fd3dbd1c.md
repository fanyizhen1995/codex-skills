---
source_id: sglang-github-closed-issues-prs
title: 'feat(parser): resolve special-token suffix at runtime for compatibility'
canonical_url: https://github.com/sgl-project/sglang/pull/29920
captured_at: '2026-07-05T02:14:10.239807+00:00'
content_hash: c0fd3dbd1ccf5d6927e5aaeb235b62a0d2906c4aa25eb8cddea63e8d593c41f9
---
# feat(parser): resolve special-token suffix at runtime for compatibility

URL: https://github.com/sgl-project/sglang/pull/29920
State: closed
Labels: run-ci
Closed at: 2026-07-04T16:13:47Z
Merged at: 2026-07-04T16:13:47Z

## Motivation

Some tokenizers append a shared suffix to every special token (e.g. `<tool_calls:TAG>` instead of `<tool_calls>`). The `hunyuan` reasoning/tool-call detectors and the `--tool-call-parser auto` rule hard-coded the bare literals, so both parsing and auto-detection broke on such tokenizers. Resolving the real token strings from the vocab at runtime is preferable to hard-coding a per-model suffix.

## Changes

- `resolve_hunyuan_tokens(tokenizer)`: scan the vocab for the real (possibly suffixed) token strings, falling back to bare literals — one detector serves both suffix-less and suffixed tokenizers.
- Plumb an optional `tokenizer` through `ReasoningParser` / `FunctionCallParser` (via `inspect`, so non-hunyuan detectors are untouched).
- `_is_hunyuan` matches bare or suffixed `tool_calls`/`tool_sep` via regex, so `--tool-call-parser auto` still resolves to `hunyuan`.
- `structure_info` uses the resolved tokens; 16 call-sites pass `tokenizer=`.

## Verification

pre-commit + py_compile pass; `tokenizer=None` reproduces the previous token values exactly (backward compatible); e2e confirms auto-detection, tool-call/reasoning parsing, and stop-rate all work on a suffixed tokenizer.









































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28694968273](https://github.com/sgl-project/sglang/actions/runs/28694968273)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28694968200](https://github.com/sgl-project/sglang/actions/runs/28694968200)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
