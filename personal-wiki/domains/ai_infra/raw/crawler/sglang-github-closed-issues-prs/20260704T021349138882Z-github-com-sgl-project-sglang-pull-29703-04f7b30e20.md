---
source_id: sglang-github-closed-issues-prs
title: '[Anthropic] Fix missing cache_read_input_tokens in streaming responses'
canonical_url: https://github.com/sgl-project/sglang/pull/29703
captured_at: '2026-07-04T02:13:49.138882+00:00'
content_hash: 04f7b30e20fc0a1c20a1530d98caa01bd1fcfeccc2b2aaeee0a05feae6c13cce
---
# [Anthropic] Fix missing cache_read_input_tokens in streaming responses

URL: https://github.com/sgl-project/sglang/pull/29703
State: closed
Labels: run-ci
Closed at: 2026-07-03T04:46:46Z
Merged at: 2026-07-03T04:46:46Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

Streaming chat completions with `continuous_usage_stats` (i.e. `stream_options.include_usage` with per-chunk usage) never populated `prompt_tokens_details.cached_tokens` in the per-chunk `usage`. Only the **non-streaming** path (`UsageProcessor.calculate_response_usage`) and the **final** usage-only chunk (`UsageProcessor.calculate_streaming_usage`) reported cached tokens; the per-chunk `calculate_token_usage(...)` calls in the continuous-usage path were missing the `cached_tokens` argument, so `prompt_tokens_details` was always `None`.

This is harmless on the OpenAI route (clients read the final usage chunk), but it **silently breaks the Anthropic `/v1/messages` streaming route**, which delegates to `OpenAIServingChat` with `continuous_usage_stats=True`:

- The Anthropic adapter builds `message_start.message.usage` from the **first** continuous-usage chunk (`anthropic/serving.py`, `_message_start_event(chunk.usage)`), mapping `prompt_tokens_details.cached_tokens` → `cache_read_input_tokens`.
- The final usage-only chunk is mapped to `message_delta` with `include_input=False`, which intentionally drops the input/cache fields.

So the per-chunk continuous usage is the **only** channel through which `cache_read_input_tokens` can reach an Anthropic streaming client — and it was always empty. As a result, on a prefix-cache hit:

- `cache_read_input_tokens` was missing entirely (the cache benefit was invisible to the client), and
- `input_tokens` was over-reported as the full prompt, because Anthropic `input_tokens = prompt_tokens − cached_tokens` (`_anthropic_input_tokens`).

The non-streaming Anthropic path was already correct; this PR fixes the streaming path.

## Modifications

<!-- Detail the changes made in this pull request. -->

`python/sglang/srt/entrypoints/openai/serving_chat.py`
- Add helper `OpenAIServingChat._continuous_usage_cached_details(content)` that returns atokens=...)` when `enable_cache_report` is on and the chunk carries cached tokens,otherwise `None`. The gating and the "only attach when non-zero" behavior mirror `UsageProcessor._details_if_cached`, keeping plain-text usage `prompt_tokens_details=None` (backward compatible).
- Pass it as `cached_tokens=` to all five per-chunk `calculate_token_usage(...)` continuog delta, plain content delta, trailing-logprobs flush, tool-call normal text, and tool-call argument delta.
- Import `PromptTokensDetails`.

`test/registered/unit/entrypoints/openai/test_serving_chat.py`
- `test_continuous_usage_reports_cached_tokens`: with `enable_cache_report=True`, continuous-usage chunks expose `usage.prompt_tokens_details.cached_tokens`.
- `test_continuous_usage_omits_cached_tokens_when_report_disabled`: with reporting off, `absent (no leak).

**End-to-end verification on a live server** (`Qwen3` MoE FP8, `tp=2`, `--enable-cache-report`): the same ~1098-token prompt sent twice over the Anthropic streaming endpoint, observing `message_start.usage` on
the warm (prefix-cache hit) request:

| Build | `input_tokens` | `cache_read_input_tokens` |
| --- | ---: | ---: |
| Before (this PR reverted) | 1098 | absent / 0 |
| After  (this PR)          | 10   | 1088 |

The cold (first) request reports `input_tokens=1098 / cache_read=0` in both builds, confiche reads when they actually occur. Cross-check: reverting only the source change makes
`test_continuous_usage_reports_cached_tokens` fail, confirming the new test guards the re

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

N/A — this changes usage/token accounting only; model forward and token generation are un unchanged.

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

N/A — no hot-path or kernel changes. The added helper is a dict lookup gated by `enable_cache_report`.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglangion_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/devde.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](httpsuide/contribution_guide.html#test-the-accuracy) and [Benchmark thespeed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/conte-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.githuwers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_gests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permissi































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28437310181](https://github.com/sgl-project/sglang/actions/runs/28437310181)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28437310100](https://github.com/sgl-project/sglang/actions/runs/28437310100)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
