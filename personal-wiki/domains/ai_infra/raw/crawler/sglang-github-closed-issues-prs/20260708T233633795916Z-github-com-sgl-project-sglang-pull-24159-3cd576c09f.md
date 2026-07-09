---
source_id: sglang-github-closed-issues-prs
title: '[Router] Fix PD router hang when prefill server returns error'
canonical_url: https://github.com/sgl-project/sglang/pull/24159
captured_at: '2026-07-08T23:36:33.795916+00:00'
content_hash: 3cd576c09f6c852ad8cd6894964749388027309583c1728f28ab53c67412fa12
---
# [Router] Fix PD router hang when prefill server returns error

URL: https://github.com/sgl-project/sglang/pull/24159
State: closed
Labels: model-gateway
Closed at: 2026-07-08T07:19:52Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

This patch is for 

- Fix a hang in PD disaggregation mode where the router blocks forever if the prefill server returns a non-2xx response (e.g. 400 Bad Request)
- Replace `tokio::join!` with `tokio::select!` in `execute_dual_dispatch_internal` to detect prefill failure early and cancel the decode request immediately


## Motivation

<!-- Describe the purpose and goals of this pull request. -->

In PD (prefill-decode) disaggregation mode, the router sends requests to both prefill and decode servers concurrently using `tokio::join!`. The decode server depends on receiving the KV cache from the prefill server before it can produce a response.

If the prefill server rejects the request (e.g. input exceeds context length → 400, or any other error), the KV cache transfer never happens. The decode server then waits indefinitely for KV data that will never arrive, and `tokio::join!` blocks forever because the decode future never completes. This causes the entire request to hang in the router until the HTTP client timeout (default 1800s), effectively making the benchmark or client appear stuck at ~100% progress.

This was observed in production with 40960-prompt benchmarks where a small number of requests hit the context length boundary (`input_tokens + output_tokens == context_length`), causing the prefill server to return 400. The benchmark would hang at 40959/40960 indefinitely.

## Modifications

<!-- Detail the changes made in this pull request. -->
Replace `tokio::join!` with `tokio::select!` to race the prefill and decode futures:
- If **prefill completes first with an error**: immediately return the error to the client. The decode future is dropped (cancelled) on return, preventing the hang.
- If **prefill completes first with success**: wait for decode normally (same as before).
- If **decode completes first**: wait for prefill (same as before).

This preserves the concurrent dispatch behavior on the happy path while adding early termination on prefill failure.


## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.
