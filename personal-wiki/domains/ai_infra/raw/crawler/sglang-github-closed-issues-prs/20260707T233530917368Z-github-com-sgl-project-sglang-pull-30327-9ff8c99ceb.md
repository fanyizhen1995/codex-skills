---
source_id: sglang-github-closed-issues-prs
title: '[PD][NIXL] Propagate prefill transfer failures'
canonical_url: https://github.com/sgl-project/sglang/pull/30327
captured_at: '2026-07-07T23:35:30.917368+00:00'
content_hash: 9ff8c99cebb5f6aa07aaaf2e291360e792bd5ff8e8ebef82cee688259251cb59
---
# [PD][NIXL] Propagate prefill transfer failures

URL: https://github.com/sgl-project/sglang/pull/30327
State: closed
Labels: 
Closed at: 2026-07-07T04:24:36Z
Merged at: 

## Motivation

When a NIXL transfer fails on the prefill side after bootstrap, only the prefill room is marked failed. Decode receives no terminal signal, remains in `KVPoll.WaitingForInput` until its timeout, and retains the request's preallocated KV and state resources.

## Modifications

- Add an explicit prefill-to-decode failure control message for transfer exceptions and sender aborts.
- Dispatch notifications through a bounded single-worker queue so ZeroMQ sockets have one owner and failure handling remains nonblocking.
- Accept notifications only for active decode rooms, preserve the remote failure reason, and clean up per-room transfer tracking.
- Add unit coverage for active, terminal, unknown, malformed, nonblocking-send, and cleanup paths.

## Accuracy Tests

Not applicable. This change does not modify model computation or outputs.

## Speed Tests and Profiling

Not applicable. The new work is limited to transfer failure handling; the successful transfer path is unchanged.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations). Not applicable; there is no user-facing behavior or configuration change.
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed). Both are not applicable for this failure-path-only change.
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28839339760](https://github.com/sgl-project/sglang/actions/runs/28839339760)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28839339734](https://github.com/sgl-project/sglang/actions/runs/28839339734)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
