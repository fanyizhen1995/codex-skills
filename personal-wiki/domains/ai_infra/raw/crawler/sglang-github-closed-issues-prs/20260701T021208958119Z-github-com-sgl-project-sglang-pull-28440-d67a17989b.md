---
source_id: sglang-github-closed-issues-prs
title: '[Mooncake] Add try/except guard to decode status thread'
canonical_url: https://github.com/sgl-project/sglang/pull/28440
captured_at: '2026-07-01T02:12:08.958119+00:00'
content_hash: d67a17989b07c7865fea3d31be5023a00db4db76f28e05b8930e3b14da993f81
---
# [Mooncake] Add try/except guard to decode status thread

URL: https://github.com/sgl-project/sglang/pull/28440
State: closed
Labels: 
Closed at: 2026-06-30T11:58:12Z
Merged at: 

## Motivation

`MooncakeKVManager.start_decode_thread` runs the decode-side status worker for Mooncake disaggregation. This worker consumes ZMQ control messages from prefill workers and advances decode-side KV transfer state from `WaitingForInput` to `Success` or `Failed`.

Previously, the loop body had no exception guard. A single malformed or unexpected control message could raise during message indexing, tuple unpacking, integer decoding, staging handling, or response-count lookup. That exception would terminate the status thread, while the process itself kept running. Once the thread exits, later prefill status messages are no longer processed and requests can remain waiting for KV transfer completion until timeout.

## Modifications

- Wrap each decode status thread iteration in `try/except Exception`.
- Log unexpected per-message failures with `logger.exception(...)`.
- Keep the existing message protocol and status update behavior unchanged.
- Add a CPU unit test that feeds one malformed status message followed by a valid success message and verifies the worker continues to process the valid message.

## Accuracy Tests

N/A. 

## Speed Tests and Profiling

N/A. 
## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations). (N/A)
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed). (N/A)
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #27625004190](https://github.com/sgl-project/sglang/actions/runs/27625004190)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27625004253](https://github.com/sgl-project/sglang/actions/runs/27625004253)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
