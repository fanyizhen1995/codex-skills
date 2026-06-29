---
source_id: sglang-github-closed-issues-prs
title: 'shm_broadcast: bind XPUB port atomically to avoid pinned-port race'
canonical_url: https://github.com/sgl-project/sglang/pull/29547
captured_at: '2026-06-29T04:09:41.035065+00:00'
content_hash: 6cc8fc0aa473dafc0745be53de92e076516705fa37627c1d4ee7bd0946c047cc
---
# shm_broadcast: bind XPUB port atomically to avoid pinned-port race

URL: https://github.com/sgl-project/sglang/pull/29547
State: closed
Labels: run-ci
Closed at: 2026-06-28T05:25:50Z
Merged at: 

## Summary

When `SGLANG_PORT` is pinned and multiple `MessageQueue` writers start
concurrently on the same node, the XPUB local socket setup uses
`get_open_port()` followed by a later `bind()` — a non-atomic
check-then-bind. Two writers can be handed the same port and then collide
on `bind()` with `EADDRINUSE`.

One scheduler subprocess dies at init:

```
zmq.error.ZMQError: Address already in use (addr='tcp://127.0.0.1:50000')
  File ".../sglang/srt/distributed/parallel_state.py", line 464, in __init__
    self.mq_broadcaster = MessageQueue.create_from_process_group(self.cpu_group, 1 << 22, 6)
  File ".../sglang/srt/distributed/device_communicators/shm_broadcast.py", line 214, in __init__
    self.local_socket.bind(socket_addr)
```

which then cascades into a gloo failure on every rank:

```
RuntimeError: [gloo/transport/tcp/pair.cc] Connection reset by peer
  File ".../sglang/srt/model_executor/model_runner.py", line 1189, in get_available_gpu_memory
    torch.distributed.all_reduce(tensor, op=ReduceOp.MIN, group=group)
```

This replaces `get_open_port()` + `bind()` with zmq's `bind_to_random_port`,
which picks and binds a free port atomically. When `SGLANG_PORT` is set the
search starts at that base (`min=base`, `max=base + 8`) to preserve the
existing port range; otherwise it falls back to the default ephemeral range.

A similar atomic fix is proposed upstream in #15885 (PR #15903).

## Test

Concurrent `MessageQueue` writers under a pinned `SGLANG_PORT` no longer
hit the `EADDRINUSE` error; each binds a distinct port.



<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->_Not run yet_<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:warning: **Not enabled** -- add `run-ci-extra` label to opt in.<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
