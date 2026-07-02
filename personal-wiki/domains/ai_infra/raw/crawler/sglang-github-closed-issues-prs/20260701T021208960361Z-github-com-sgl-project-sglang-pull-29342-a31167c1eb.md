---
source_id: sglang-github-closed-issues-prs
title: Add native Exa-backed web_search support
canonical_url: https://github.com/sgl-project/sglang/pull/29342
captured_at: '2026-07-01T02:12:08.960361+00:00'
content_hash: a31167c1ebcf35adef16aba6005507d60243e0806df070c365ac05388f7747a9
---
# Add native Exa-backed web_search support

URL: https://github.com/sgl-project/sglang/pull/29342
State: closed
Labels: documentation, high priority, run-ci, release-highlight
Closed at: 2026-06-27T13:41:10Z
Merged at: 2026-06-27T13:41:10Z

## Summary

Adds native `web_search` support for GPT-OSS/SGLang Responses workflows, backed by Exa when `EXA_API_KEY` is configured on the SGLang server.

This keeps the user-facing abstraction provider-neutral (`web_search`) while using Exa as the default native backend for the existing hosted browser tool path. MCP tool servers remain available for advanced/custom tool configurations.

## Details

- Adds a centralized Exa client for Search and Contents API calls.
- Enables BYOK via server-side `EXA_API_KEY`.
- Tags Exa requests with `x-exa-integration: sglang`.
- Uses server-side defaults:
  - `numResults=10`
  - `type="auto"`
  - highlights enabled
- Adds native hosted browser tool support when no external tool server is configured.
- Keeps provider details out of model-facing tool output.
- Returns a clear error when `web_search` is requested without a browser backend.
- Documents native web search setup and optional server-side Exa tuning env vars.

## Tests

- `python -m py_compile` on changed Python files
- `git diff --check`
- No-network framework smoke for `NativeToolServer -> HarmonyBrowserTool -> ExaClient`
- Live Exa smoke through `NativeToolServer -> HarmonyBrowserTool -> ExaClient -> Exa`















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28281139432](https://github.com/sgl-project/sglang/actions/runs/28281139432)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:hourglass_flowing_sand: [Run #28429641199](https://github.com/sgl-project/sglang/actions/runs/28429641199)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
