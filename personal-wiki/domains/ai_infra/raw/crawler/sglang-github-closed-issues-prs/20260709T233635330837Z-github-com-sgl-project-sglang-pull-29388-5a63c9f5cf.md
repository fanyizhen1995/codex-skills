---
source_id: sglang-github-closed-issues-prs
title: '[Test] Add unit tests for OpenAI rerank serving helpers'
canonical_url: https://github.com/sgl-project/sglang/pull/29388
captured_at: '2026-07-09T23:36:35.330837+00:00'
content_hash: 5a63c9f5cfdce239ab737253ba7c4734d2e31ea3a2ae139be2253ed899bcbba6
---
# [Test] Add unit tests for OpenAI rerank serving helpers

URL: https://github.com/sgl-project/sglang/pull/29388
State: closed
Labels: 
Closed at: 2026-07-09T09:52:42Z
Merged at: 

## Summary

Add CPU-only unit tests for `serving_rerank.py`, covering:
- Qwen3/Qwen3-VL reranker template detection
- rerank backend routing
- yes/no token id fallback
- score extraction from logprobs
- multimodal content conversion
- cross-encoder request conversion
- response sorting, `top_n`, and `return_documents`

Part of #20865.

## Tests

```bash
pytest test/registered/unit/entrypoints/openai/test_serving_rerank.py -v















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28221446337](https://github.com/sgl-project/sglang/actions/runs/28221446337)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28221446235](https://github.com/sgl-project/sglang/actions/runs/28221446235)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
