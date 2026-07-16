---
source_id: sglang-github-closed-issues-prs
title: '[Feature] Add --default-chat-template-kwargs server arg'
canonical_url: https://github.com/sgl-project/sglang/pull/29579
captured_at: '2026-07-13T23:40:05.178983+00:00'
content_hash: c3674ce5c3b7e4f19a2d1be40c669c656565ac779107a5b63ff498dd85e8e0ac
---
# [Feature] Add --default-chat-template-kwargs server arg

URL: https://github.com/sgl-project/sglang/pull/29579
State: closed
Labels: run-ci
Closed at: 2026-07-13T18:34:39Z
Merged at: 2026-07-13T18:34:39Z

## Motivation

There is currently no way to disable thinking (or set any chat template kwarg) once at server launch and have it apply to every request by default. Today operators must either:

- pass `chat_template_kwargs={"enable_thinking": false}` on **every** client request, or
- set the `SGLANG_DEFAULT_THINKING` env var, which only covers the `thinking` key (not `enable_thinking` used by Qwen3 / GLM-4.5 / GLM-5.2) and is not a CLI flag.

This adds a `--default-chat-template-kwargs` server arg so a single launch flag (e.g. `--default-chat-template-kwargs '{"enable_thinking": false}'`) makes the default apply to all requests without per-request changes.

## Changes

- `ServerArgs.default_chat_template_kwargs` (CLI `--default-chat-template-kwargs`, JSON dict, `type_parser=json.loads`).
- `OpenAIServingChat` reads it in `__init__` and merges it into `request.chat_template_kwargs` at the top of `_process_messages` with **setdefault** semantics, so per-request `chat_template_kwargs` and `reasoning_effort` (which the protocol validator already folds into `chat_template_kwargs`) still take precedence.
- `_process_messages` is the shared entry point for the OpenAI Chat, Responses, Anthropic, and tokenize paths, so one injection point covers all of them.
- Two unit tests in `test_serving/unit/entrypoints/openai/test_serving_chat.py`: default is applied when the request omits `chat_template_kwargs`, and a per-request value overrides the default.

## Usage

```bash
python -m sglang.launch_server --model-path ... --default-chat-template-kwargs '{"enable_thinking": false}'
```

Precedence: per-request `chat_template_kwargs` > `reasoning_effort` > `--default-chat-template-kwargs` > template default.





























































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28919966285](https://github.com/sgl-project/sglang/actions/runs/28919966285)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28919966174](https://github.com/sgl-project/sglang/actions/runs/28919966174)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
