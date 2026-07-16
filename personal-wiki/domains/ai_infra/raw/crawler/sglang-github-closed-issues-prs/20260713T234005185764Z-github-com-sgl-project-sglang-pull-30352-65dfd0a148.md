---
source_id: sglang-github-closed-issues-prs
title: Handle NIXL abort notifications
canonical_url: https://github.com/sgl-project/sglang/pull/30352
captured_at: '2026-07-13T23:40:05.185764+00:00'
content_hash: 65dfd0a148b78817f19abb3402d888436d8be2163062b95f51ee922ad426a5f0
---
# Handle NIXL abort notifications

URL: https://github.com/sgl-project/sglang/pull/30352
State: closed
Labels: 
Closed at: 2026-07-13T12:05:25Z
Merged at: 2026-07-13T12:05:25Z

## Motivation

NIXL disaggregation can receive a decode-side abort while the prefill transfer worker is still finishing a KV/aux transfer. Without handling the abort prefill bootstrap_thread can fail with assertion error ('ABORT' not recognized). Follow up to https://github.com/sgl-project/sglang/pull/27372 that initially introduced abort msg

## Modifications

- Handle `ABORT` messages on the NIXL prefill bootstrap socket and mark incomplete rooms as `Failed`.
- Keep NIXL `Failed` status sticky until the sender clears the room.
- Do not send `ABORT_ACK` on the NIXL path yet; there is no defined NIXL quiescence/deferred-release contract for safely acknowledging decode-side buffer release, so this PR leaves a TODO instead.
- Add CPU unit coverage for abort handling, sticky failed status, and mid-transfer abort races.

## Accuracy Tests

Not applicable; this only changes disaggregation control-plane state handling.

## Speed Tests and Profiling

Not applicable; no inference hot path changes.

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28922034696](https://github.com/sgl-project/sglang/actions/runs/28922034696)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28922034519](https://github.com/sgl-project/sglang/actions/runs/28922034519)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
