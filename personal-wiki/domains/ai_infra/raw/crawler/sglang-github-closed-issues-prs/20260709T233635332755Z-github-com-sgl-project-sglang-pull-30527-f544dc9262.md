---
source_id: sglang-github-closed-issues-prs
title: 'fix(tool_call): recover complete DSv32 tool calls dropped on max_tokens truncation'
canonical_url: https://github.com/sgl-project/sglang/pull/30527
captured_at: '2026-07-09T23:36:35.332755+00:00'
content_hash: f544dc9262ead4080bc9bf9605228b1832f5a74648b18ec0cdd9cec6dad47564
---
# fix(tool_call): recover complete DSv32 tool calls dropped on max_tokens truncation

URL: https://github.com/sgl-project/sglang/pull/30527
State: closed
Labels: deepseek
Closed at: 2026-07-09T09:17:17Z
Merged at: 

# Motivation

While running DeepSeek-V3.2 agent loops with tight `max_tokens` budgets, non-streaming responses intermittently came back with **empty `tool_calls`** even though the model had clearly emitted complete tool calls before hitting the token limit. The same requests with `stream=true` returned the calls normally.

Root cause (reproduced at detector level, CPU-only, current main): when the output is truncated by `max_tokens`, the closing `</｜DSML｜function_calls>` tag never arrives, so `detect_and_parse`'s `function_calls_regex` fails to match and **every** invoke block in the response is silently discarded — including calls that completed before the cutoff:

```python
D = "｜DSML｜"
# one COMPLETE call + one truncated by max_tokens
text = (f"Check both.<{D}function_calls>"
  f'<{D}invoke name="get_weather"><{D}parameter name="city" string="true">Paris</{D}parameter></{D}invoke>'
  f'<{D}invoke name="get_weather"><{D}parameter name="city" string="true">San Fr')
DeepSeekV32Detector().detect_and_parse(text, tools)
# before: calls=[]                      <- complete Paris call silently lost
# after:  calls=[get_weather(city=Paris)]
```

This is the DSv32 variant of the failure class just reported in #30480 (hermes/qwen25): non-streaming behavior diverges from streaming when a tool call is cut off by `max_tokens`. For DSv32 it is arguably worse — instead of leaking markup into `content`, it **drops valid completed calls**, so agent clients (LangChain / AI SDK / Continue, etc.) see an assistant turn with no tool calls and no explanation.

# Modifications

`python/sglang/srt/function_call/deepseekv32_detector.py` (`detect_and_parse` only; streaming path already handles this correctly):

1. When the closing `function_calls` tag is missing (truncated output), fall back to parsing the content after the opener instead of returning early, so complete invoke blocks are still recovered.
2. Use the existing `is_complete` flag from `_unpack_invoke_match` (previously ignored via `_`) to drop the trailing unterminated invoke rather than emitting a call with partial arguments — matching the streaming path's behavior. Complete-but-malformed blocks keep the current documented fallback (existing tests unchanged).

`test/registered/unit/function_call/test_function_call_parser.py`: 5 new unit tests in `TestDeepSeekV32Detector` covering: complete call surviving a truncated neighbor, single truncated call dropped cleanly, truncation right at the opener, truncated direct-JSON format, and a self-closing invoke with missing closing wrapper tag.

# Accuracy Tests

Detector-level unit tests (CPU-only):

```
pytest test/registered/unit/function_call/test_function_call_parser.py -k "DeepSeekV32"
# 13 passed (8 existing + 5 new); test_get_model_structural_tag requires xgrammar, unrelated
```

Full `test_function_call_parser.py` run has no new failures vs. clean main (verified via `git stash` A/B).

# Speed Tests and Profiling

N/A — no hot-path change; one extra branch in the non-streaming final parse.

# Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

---

Related: #30480 (same failure class in hermes/qwen25; that fix is scoped to those detectors, this PR covers the DSv32 side).

cc @CatherineSue @JustinTong0323







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28941268692](https://github.com/sgl-project/sglang/actions/runs/28941268692)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28941268586](https://github.com/sgl-project/sglang/actions/runs/28941268586)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
