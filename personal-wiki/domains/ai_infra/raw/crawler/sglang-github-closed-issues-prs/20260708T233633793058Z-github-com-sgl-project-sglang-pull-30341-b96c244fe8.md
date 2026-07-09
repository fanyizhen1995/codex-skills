---
source_id: sglang-github-closed-issues-prs
title: '[server] Widen streaming-kickstart to preserve HTTPException status'
canonical_url: https://github.com/sgl-project/sglang/pull/30341
captured_at: '2026-07-08T23:36:33.793058+00:00'
content_hash: b96c244fe868ec54290cf8c0d013b97ebcee82507cb9f407fbf29ee8a0557b40
---
# [server] Widen streaming-kickstart to preserve HTTPException status

URL: https://github.com/sgl-project/sglang/pull/30341
State: closed
Labels: 
Closed at: 2026-07-08T09:59:48Z
Merged at: 

## Summary

Pre-first-chunk errors in `/v1/chat/completions` and `/v1/completions` now surface with their real HTTP status code instead of falling into a `200 OK` + SSE-body error payload.

## Motivation

The pre-first-chunk kickstart in `serving_chat.py` / `serving_completions.py` currently catches only `ValueError`:

```python
try:
    first_chunk = await generator.__anext__()
except ValueError as e:
    return self.create_error_response(str(e))    # → HTTP 400
```

Any other engine-side pre-stream error (rate limit, capacity, disaggregation encoder returning 503, etc.) doesn't match `ValueError`, so it either falls through to FastAPI's default 500 handler or — if the exception is caught deeper in the generator — gets turned into a `data: {...}` SSE frame emitted under a HTTP 200 header. That is the origin of "the engine emitted the 503 directly into its own SSE body": headers are already committed to `text/event-stream`, so nothing downstream can turn the response back into a real HTTP error.

## Fix

Catch `Exception` in the kickstart and route through a shared helper `create_error_response_for_stream_kickstart()` on `OpenAIServingBase`:

| Exception type | Response status |
|---|---|
| `HTTPException(status_code=N)` | Preserves `N` (429, 503, 504, ...) with `detail` as message |
| `ValueError` | 400 (**unchanged from prior behavior**) |
| Any other `Exception` | 500 InternalServerError |

Mid-stream errors (once `stream_started=True`) are **unchanged**: those must stay as SSE-body errors because the `200 OK` header is already on the wire and the socket is committed to `text/event-stream`.

## Backward compatibility

- Existing `ValueError → 400` mapping is preserved (regression-guard test added).
- Any pre-first-chunk exception that previously bubbled to FastAPI's default 500 handler now goes through our helper and gets a clean OpenAI-shaped error body with the same 500 status. Structured error response instead of raw stack trace — no behavior loss.

## Test plan
- [x] `pytest test/registered/unit/utils/test_stream_kickstart_error_mapping.py` — 4 passed
  - `ValueError → 400` (backward-compat regression guard)
  - `HTTPException(503) → 503`
  - `HTTPException(429) → 429`
  - `RuntimeError → 500`
- [x] Pre-commit clean

🤖 Generated with [Claude Code](https://claude.com/claude-code)















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28844320792](https://github.com/sgl-project/sglang/actions/runs/28844320792)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28844320704](https://github.com/sgl-project/sglang/actions/runs/28844320704)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
