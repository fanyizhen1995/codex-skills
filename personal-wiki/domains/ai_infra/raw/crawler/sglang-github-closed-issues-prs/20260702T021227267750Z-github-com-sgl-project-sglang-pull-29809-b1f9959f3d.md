---
source_id: sglang-github-closed-issues-prs
title: Add OpenAI-compatible tokenize endpoints
canonical_url: https://github.com/sgl-project/sglang/pull/29809
captured_at: '2026-07-02T02:12:27.267750+00:00'
content_hash: b1f9959f3d3ffd34da613d697f19ade0d1a8af9e978cdda9f06da96f0d54ee63
---
# Add OpenAI-compatible tokenize endpoints

URL: https://github.com/sgl-project/sglang/pull/29809
State: closed
Labels: 
Closed at: 2026-07-01T05:52:12Z
Merged at: 

## Motivation

Add OpenAI-compatible tokenize endpoints that return the token ids produced by the same request preprocessing path used by `/v1/chat/completions` and `/v1/completions`, without dispatching the request to scheduler forward execution.

## Modifications

- Add `/v1/chat/tokenize` and `/v1/completions/tokenize` endpoints.
- Update `/v1/tokenize` to dispatch internally based on `messages` vs `prompt`.
- Reuse the existing chat/completions validation and `_convert_to_internal_request` paths before tokenization.
- Add `TokenizerManager.tokenize_request()` to return prompt token ids after tokenizer-side processing and clean up request state without sending to the scheduler.
- Add unit and server tests for routing, conversion-path reuse, no-forward tokenization, generic dispatch, and prompt-token consistency.

## Accuracy Tests

N/A. This PR does not change model forward computation.

## Speed Tests and Profiling

N/A. This PR adds tokenization-only endpoints and does not change inference kernels or scheduler forward execution.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

Local validation:

- `PYTHONPATH=/private/tmp/sglang-test-stubs:python /private/tmp/sglang-tokenize-venv/bin/python test/registered/unit/managers/test_tokenizer_manager_rid_cleanup.py TestTokenizeRequestWithoutGeneration -v`
- `PYTHONPATH=/private/tmp/sglang-test-stubs:python /private/tmp/sglang-tokenize-venv/bin/python test/registered/unit/entrypoints/openai/test_serving_tokenize.py -v`
- `PYTHONPATH=/private/tmp/sglang-test-stubs:python /private/tmp/sglang-tokenize-venv/bin/python -m py_compile python/sglang/srt/entrypoints/http_server.py python/sglang/srt/entrypoints/openai/protocol.py python/sglang/srt/entrypoints/openai/serving_tokenize.py python/sglang/srt/managers/tokenizer_manager.py test/registered/unit/managers/test_tokenizer_manager_rid_cleanup.py test/registered/unit/entrypoints/openai/test_serving_tokenize.py test/registered/openai_server/basic/test_openai_server.py`
- `git diff --check origin/main..HEAD`

Note: GPU-backed OpenAI server integration tests are included for CI coverage but were not run locally because this machine has no CUDA device (`torch.cuda.is_available() == False`).







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28496635951](https://github.com/sgl-project/sglang/actions/runs/28496635951)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28496635828](https://github.com/sgl-project/sglang/actions/runs/28496635828)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
