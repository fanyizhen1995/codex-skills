---
source_id: sglang-github-closed-issues-prs
title: '[refactor] hoist force_nonempty_content into BaseReasoningFormatDetector'
canonical_url: https://github.com/sgl-project/sglang/pull/30544
captured_at: '2026-07-13T23:40:05.183264+00:00'
content_hash: b1708eeff7f0317b88b8842668885e652568a24fe62e028da094350c13bf5398
---
# [refactor] hoist force_nonempty_content into BaseReasoningFormatDetector

URL: https://github.com/sgl-project/sglang/pull/30544
State: closed
Labels: 
Closed at: 2026-07-13T13:52:53Z
Merged at: 

## Motivation

`force_nonempty_content` (introduced in #20284) is a per-request opt-in flag (`chat_template_kwargs={"force_nonempty_content": True}`) that reclassifies reasoning as content when the model emits no normal text — for code agents that only read the `content` field. Two problems with the current state:

1. The non-streaming swap logic is **copy-pasted** across `Nemotron3Detector` and `Apertus2509Detector`.
2. `ReasoningParser.__init__` passes the kwarg **unconditionally** with no `inspect.signature` guard, so setting it on any model other than Nemotron3/Apertus (`qwen3`, `deepseek`, ...) crashes with `TypeError: __init__() got an unexpected keyword argument 'force_nonempty_content'`.
3. Streaming truncation (model hits `max_tokens` mid-reasoning, no closing think token) was only handled for Nemotron3 via a bespoke override; Apertus had no streaming coverage at all.

## Modifications

- Move `force_nonempty_content` into `BaseReasoningFormatDetector.__init__` and centralize the non-streaming swap in a single `_apply_force_nonempty` helper applied at every `detect_and_parse` return path.
- Generalize the streaming truncation path: base `finish()` now reclassifies accumulated reasoning + buffered residue as content when the stream ends mid-reasoning. Adds `parse_stream_end()` to `ReasoningParser` and wires `finish_reason_type` through `_process_reasoning_stream` so the flush fires on the final chunk (skipping graceful abort).
- Thread `force_nonempty_content` through all detector subclasses so the flag is accepted by every model instead of crashing.

`Nemotron3Detector` drops its `detect_and_parse` / `parse_streaming_increment` / `finish` overrides entirely (now pure inheritance). `Apertus2509Detector` keeps its custom streaming state machine (no `super()` call), so streaming truncation there remains a known gap to be addressed separately.

## Behavior note

Streaming `finish()` re-emits already-streamed reasoning as `content` (so reasoning appears in both `reasoning_content` and `content` when truncated). This matches the original #20284 motive — code agents that only read `content` get a non-empty response. Non-streaming does a clean swap (no duplication). This stream/non-stream divergence is intentional for the truncation case; flagging for reviewer awareness.

## Tests

- Adds base-level + `Apertus2509Detector` non-streaming swap tests (Apertus had zero `force_nonempty_content` coverage before).
- Existing Nemotron3 `force_nonempty_content` tests remain green (base behavior is equivalent).

## Checklist

- [ ] Format code with pre-commit
- [ ] Add / update tests
- [ ] Update docs

Draft — seeking early feedback on the hoist + the streaming `finish()` generalization before finalizing.































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28959216089](https://github.com/sgl-project/sglang/actions/runs/28959216089)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28959215998](https://github.com/sgl-project/sglang/actions/runs/28959215998)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
