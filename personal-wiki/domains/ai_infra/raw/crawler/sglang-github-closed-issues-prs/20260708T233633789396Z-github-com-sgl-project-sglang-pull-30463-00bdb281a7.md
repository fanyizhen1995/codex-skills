---
source_id: sglang-github-closed-issues-prs
title: '[Bugfix] Map reasoning_effort=low to Nemotron-3 Super low_effort + warn on
  unsupported levels'
canonical_url: https://github.com/sgl-project/sglang/pull/30463
captured_at: '2026-07-08T23:36:33.789396+00:00'
content_hash: 00bdb281a71a5b5f46887aa05af5d6a8e2c7c5efc043aeee7175a1756e32479c
---
# [Bugfix] Map reasoning_effort=low to Nemotron-3 Super low_effort + warn on unsupported levels

URL: https://github.com/sgl-project/sglang/pull/30463
State: closed
Labels: run-ci
Closed at: 2026-07-08T19:19:44Z
Merged at: 2026-07-08T19:19:44Z

Builds on #28860, which fixed the generic `reasoning_effort` → thinking-toggle path. That PR makes `low/medium/high/max` set `enable_thinking=True`, but does not address the **Nemotron-3 Super** `low_effort` level.

## Problem

Nemotron-3 Super's chat template exposes a boolean `low_effort` that, when true, injects `{reasoning effort: low}` into the last user message. SGLang never mapped the OpenAI `reasoning_effort` field to it, so:

- `reasoning_effort="low"` was a silent no-op (model stayed in default thinking).
- On Nemotron-3 **Nano**, which has no effort knob at all, every non-`none` level silently fell back to default thinking.

This is the "each variant supports 1 effort level and noops the rest" behavior that downstream users (e.g. CoreWeave) hit: requests look accepted but the requested effort never takes effect, and nothing warns.

## Fix

1. **Detect Nemotron-3 Super** by the `low_effort` template marker (paired with `truncate_history_thinking` to stay within the Nemotron-3 family) and record `effort_kwarg="low_effort"` on `ReasoningToggleConfig`.
2. In `_apply_jinja_template`, when `effort_kwarg` is set:
   - `reasoning_effort="low"` → `chat_template_kwargs["low_effort"]=True` (`setdefault`, so an explicit user value still wins).
   - `reasoning_effort` ∈ {medium, high, max} → default thinking, plus a `logger.warning` that only `'low'` is supported.
3. `_is_nemotron_3` now compares `toggle_param`/`default_enabled` by field rather than strict config equality, so the Super config (which carries `effort_kwarg`) still matches the `nemotron_3` parser. Nano is unaffected (no `low_effort` marker).

`none` continues to disable thinking via #28860's `normalize_reasoning_inputs`. Nano is intentionally not warned — it has no effort knob by design, and a global warning would be noise for the qwen3/glm45 family that shares the toggle path.

## Test

- `test_template_manager.py`: Super template snippet → `effort_kwarg="low_effort"`; Nano snippet → no `effort_kwarg` (existing `test_nemotron_detects_uppercase_true_assignment` stays green).
- `test_serving_chat.py`: Super + `low` → `apply_chat_template` called with `low_effort=True`; Super + `high` → no `low_effort` + warning logged; Nano + `high` → no `low_effort`, no warning.



















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28913812718](https://github.com/sgl-project/sglang/actions/runs/28913812718)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28913812636](https://github.com/sgl-project/sglang/actions/runs/28913812636)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
