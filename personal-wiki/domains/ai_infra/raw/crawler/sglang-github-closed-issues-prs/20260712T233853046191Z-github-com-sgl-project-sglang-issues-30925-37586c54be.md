---
source_id: sglang-github-closed-issues-prs
title: '[Bug] GLM tool-call parser leaks raw <tool_call> markup into content when
  tool_choice="none"'
canonical_url: https://github.com/sgl-project/sglang/issues/30925
captured_at: '2026-07-12T23:38:53.046191+00:00'
content_hash: 37586c54be3923ff6b28f10fb8fc9408dc8fdbafadfa4d1d5437b2293daac3ce
---
# [Bug] GLM tool-call parser leaks raw <tool_call> markup into content when tool_choice="none"

URL: https://github.com/sgl-project/sglang/issues/30925
State: closed
Labels: 
Closed at: 2026-07-12T09:39:37Z
Merged at: 

### Describe the bug

When a chat completion is sent with `tool_choice: "none"` and a non-empty `tools` array, GLM-5.2 (and GLM-5.1) sometimes emit the model's native tool-call template markup (`<tool_call> ... </tool_call>` and the related fullwidth delimiter tokens) directly into `message.content` as prose, instead of a clean natural-language answer.

Because the tool-call detector is disabled when `tool_choice="none"`, any tool-call markup the model produces is not stripped, so it passes straight through into the content stream. The caller receives raw template scaffolding mixed into the assistant text.

### How to reproduce

Model `z-ai/glm-5.2` (also reproduces on GLM-5.1), SGLang `v0.5.15` (cu130):

```bash
curl -s $BASE/v1/chat/completions -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' -d '{
  "model": "z-ai/glm-5.2",
  "tool_choice": "none",
  "tools": [{"type":"function","function":{"name":"get_weather","description":"get weather","parameters":{"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}}}],
  "messages": [{"role":"user","content":"What is the weather in Dublin? Answer in one sentence, do not call any tool."}]
}'
```

Observed (repeatable with a tool-inviting prompt): `message.content` contains `<tool_call>` / `get_weather` template markup.

Expected: with `tool_choice="none"` the response is a clean natural-language answer and contains no tool-call markup, per the OpenAI semantics that `none` means the model must not call a tool.

### Suggested fix

Two options, either is fine:

1. When `tool_choice="none"`, still run the detector but in strip-only mode: remove any tool-call markup from the content stream and emit cleaned content with no `tool_calls`.
2. Fix at the GLM chat template: when tools are present but `tool_choice="none"`, do not prime the tool-call syntax.

Option 1 is the more robust, since it also covers models that emit markup unprompted.

### Environment

- SGLang v0.5.15 (cu130), Blackwell B300
- Models: GLM-5.2, GLM-5.1 (FP8)
- tool-call-parser: glm45 / glm47 family
