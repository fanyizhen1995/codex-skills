---
source_id: sglang-github-closed-issues-prs
title: 'feat: add server-wide default thinking budget ceiling API'
canonical_url: https://github.com/sgl-project/sglang/pull/19198
captured_at: '2026-07-01T02:12:08.972909+00:00'
content_hash: 598bb849aeaaf4b342f3ef3f54138bc3f48cc1c772f7c82feae6f94070a1703a
---
# feat: add server-wide default thinking budget ceiling API

URL: https://github.com/sgl-project/sglang/pull/19198
State: closed
Labels: 
Closed at: 2026-06-29T22:43:36Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Operators running thinking models (DeepSeek-R1, Qwen3, GLM-4) need a way to control thinking token costs server-wide without requiring every client to set thinking_budget per-request. Currently, thinking budget control is only available per-request via custom_params, which means:
  - No way to enforce a global ceiling across all clients
  - No way to set a default thinking budget for clients that don't specify one
  - No admin control over thinking token costs

  This PR adds a server-wide thinking budget ceiling that:
  - Clamps per-request thinking_budget to min(per_request, ceiling)
  - Applies the ceiling as default when clients don't specify a thinking_budget
  - Auto-injects the correct ThinkingBudgetLogitProcessor based on model type (Qwen3, DeepSeek-R1, GLM-4)
  - Can be updated at runtime via admin API without server restart

#19200

## Modifications

  - server_args.py: Add --default-thinking-budget CLI flag with validation; auto-enable --enable-custom-logit-processor when set
  - tokenizer_manager.py: Add init_thinking_budget_ceiling() for startup initialization, set/get_default_thinking_budget() for runtime API, clamping logic in
  _create_tokenized_object(), and model-type-based processor auto-detection via _detect_thinking_budget_processor()
  - http_server.py: Add POST /set_default_thinking_budget and GET /get_default_thinking_budget admin endpoints with @auth_level(AuthLevel.ADMIN_OPTIONAL)
  - engine.py: Add set/get_default_thinking_budget() delegating to tokenizer_manager
  - http_server_engine.py: Add HTTP-based set/get_default_thinking_budget() for HttpServerEngineAdapter
  - collector.py: Add Prometheus gauge sglang:default_thinking_budget (-1 = unlimited)
  - test_thinking_budget_ceiling.py: 29 unit tests (ServerArgs parsing, clamping logic, auto-injection, Prometheus gauge, Engine delegation) + 16 integration tests (HTTP API
  endpoints, clamping behavior with live server)

## Accuracy Tests


  Verified with Qwen3-0.6B (`--reasoning-parser qwen3 --default-thinking-budget 10000`):

  **Ceiling = 64 tokens (tight budget):**
  ```bash
  $ curl -X POST http://localhost:30000/set_default_thinking_budget \
      -H "Content-Type: application/json" -d '{"thinking_budget": 64}'
  {"success":true,"message":"Default thinking budget set to 64","thinking_budget":64}

  $ curl -s http://localhost:30000/v1/chat/completions \
      -H "Content-Type: application/json" \
      -d '{"model":"Qwen/Qwen3-0.6B","messages":[{"role":"user","content":"What is 23*47?"}],"max_tokens":1024,"temperature":0.6}'

  reasoning: 276 chars
  content: 23 × 47 = 1081 ✓
  ```

  **Ceiling = 10000 tokens (effectively unlimited):**
  ```bash
  $ curl -X POST http://localhost:30000/set_default_thinking_budget \
      -H "Content-Type: application/json" -d '{"thinking_budget": 10000}'
  {"success":true,"message":"Default thinking budget set to 10000","thinking_budget":10000}

  $ curl -s http://localhost:30000/v1/chat/completions \
      -H "Content-Type: application/json" \
      -d '{"model":"Qwen/Qwen3-0.6B","messages":[{"role":"user","content":"What is 23*47?"}],"max_tokens":1024,"temperature":0.6}'

  reasoning: 1778 chars
  content: 23 × 47 = 1081 ✓
  ```

  Lower ceiling reduces reasoning length by ~6.4x (276 vs 1778 chars) while maintaining correct output.


The model produces the correct answer with both high and low thinking budgets. Lower budget reduces reasoning length by ~6.4x while maintaining correctness on simple arithmetic. 

Thinking budget and output quality is a tradeoff, which this PR exposes to operators.

## Benchmarking and Profiling

  No performance impact on non-thinking requests — the ceiling check is a simple if self.default_thinking_budget is not None branch that short-circuits when no ceiling is configured (the default). For thinking requests, overhead is a single min() call per request.

## Checklist

- [X] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [X] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [X] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [X] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [X] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review Process

1. Ping Merge Oncalls to start the PR flow. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - `/tag-run-ci-label`, `/rerun-failed-ci`, `/tag-and-rerun-ci`
4. After green CI and required approvals, ask Merge Oncalls to merge.
