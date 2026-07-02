---
source_id: sglang-github-closed-issues-prs
title: '[passthrough] engine: zstd request-body decompression + header overrides'
canonical_url: https://github.com/sgl-project/sglang/pull/29684
captured_at: '2026-07-02T02:12:27.266026+00:00'
content_hash: 6c22c36b80eb63545169a5d491e29b673a7cebc20acd79757a308efe2ecc6aab
---
# [passthrough] engine: zstd request-body decompression + header overrides

URL: https://github.com/sgl-project/sglang/pull/29684
State: closed
Labels: dependencies, run-ci
Closed at: 2026-07-01T06:48:57Z
Merged at: 2026-07-01T06:48:57Z

Adds two optional, env-gated HTTP request-ingress features so an upstream can forward request bodies without rewriting them: (1) zstd request-body decompression, and (2) request-field overrides from headers.
## Motivation
These two features support a fan-out path where the engine's upstream (e.g. the sglang router) forwards each request to the engine **without touching the request body**:
- it passes the body through **opaque and compressed** (zstd) instead of decompressing it, and
- when it needs to override request fields (e.g. routing fields), it sets them as **headers** rather than rewriting the body.
This avoids decompressing, parsing, and re-serializing/re-compressing the body at the upstream on every request, cutting the serialization/compression overhead on the upstream→engine hop. The engine side handles both: it decompresses the body at ingress and applies the header overrides onto the parsed request. Both are **env-gated and off by default**, so default behavior is unchanged.
## Modifications
- **`entrypoints/http_request_decompression.py`** — `RequestDecompressionMiddleware`: decompresses request bodies tagged `x-body-compressed` (zstd). Mounted on the FastAPI app in `http_server.py` only when `SGLANG_ENABLE_REQUEST_DECOMPRESSION` is set.
- **`entrypoints/request_headers.py`** — `apply_header_overrides()`: overrides selected parsed request fields from request headers. Applied in `generate_request` only when `SGLANG_ENABLE_REQUEST_HEADER_OVERRIDES` is set.
- **`environ.py`** — both flags, default `False`.
- **`pyproject.toml`** — declare `zstandard` (imported at module top by the decompression middleware).
Unit tests: `test/registered/cpu/test_request_{decompression,headers}.py` — **12 passed**.
## Accuracy Tests
N/A — HTTP request-ingress plumbing only; no change to model, kernel, or forward code.
## Speed Tests and Profiling
N/A for engine inference speed — no change to the compute path. The intent is to reduce upstream→engine serialization/compression overhead (the upstream forwards the opaque compressed body + header overrides rather than decompressing and rewriting the body); both features are off by default.
## Checklist
- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations). *(N/A — env-gated, off by default)*
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed). *(N/A — no model/compute change)*
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).
## Review and Merge Process
1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28407245813](https://github.com/sgl-project/sglang/actions/runs/28407245813)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28407245640](https://github.com/sgl-project/sglang/actions/runs/28407245640)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
