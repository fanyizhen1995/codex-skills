---
source_id: sglang-github-closed-issues-prs
title: '[chore] Add no-getattr rule; refine no-dataclasses rule'
canonical_url: https://github.com/sgl-project/sglang/pull/29871
captured_at: '2026-07-02T02:12:27.252291+00:00'
content_hash: f54b7ae96bb71bdcb8266838b1a12924e7c3d71626a92b30634f1140ccf7a13e
---
# [chore] Add no-getattr rule; refine no-dataclasses rule

URL: https://github.com/sgl-project/sglang/pull/29871
State: closed
Labels: documentation
Closed at: 2026-07-01T22:31:35Z
Merged at: 2026-07-01T22:31:35Z

## Motivation

AI agents (and defensive-programming habits generally) tend to reach for `getattr` / `hasattr` on objects whose fields are always present. This hides real errors and defeats strict type checking. For example:

```python
revision=getattr(server_args, "revision", None),   # server_args ALWAYS has revision
```

This swallows an `AttributeError` if the field is ever renamed, and is confusing to readers.

## Changes

- **Add `.claude/rules/no-getattr-defensive.md`** — a concise, path-scoped (`**/*.py`) rule discouraging over-defensive `getattr`/`hasattr`. Prefers:
  1. `isinstance` for type narrowing, then direct field access.
  2. Always setting the field (to `None` if needed) and doing a `None` / non-`None` check.
  Grounded in real examples from `mm_utils.py` (good) and `template_detection.py` (bad).
- **Refine `.claude/rules/no-dataclasses.md`** — minor wording cleanup.

These are `.claude/rules/` files consumed by the `llm-rules` tooling; no runtime/source code is affected.









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28550150449](https://github.com/sgl-project/sglang/actions/runs/28550150449)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28550150116](https://github.com/sgl-project/sglang/actions/runs/28550150116)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
