---
source_id: sglang-github-closed-issues-prs
title: '[Bug] dataclass field should not put in the msgpack.Struct'
canonical_url: https://github.com/sgl-project/sglang/issues/29976
captured_at: '2026-07-03T02:13:21.689653+00:00'
content_hash: 13b991b3bb1e716dd12d2b8e9353afd548949167d969bc0e251587961a9de899
---
# [Bug] dataclass field should not put in the msgpack.Struct

URL: https://github.com/sgl-project/sglang/issues/29976
State: closed
Labels: 
Closed at: 2026-07-02T21:14:04Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

#29436 

https://github.com/sgl-project/sglang/blob/f19246e59ada26566da59d5602aa1880bf3c76b1/python/sglang/srt/managers/io_struct.py#L809

```
 File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 4219, in dispatch_event_loop
    scheduler.event_loop_overlap()
  File "/usr/local/lib/python3.12/dist-packages/torch/utils/_contextlib.py", line 124, in decorate_context
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 1576, in event_loop_overlap
    recv_reqs = self.request_receiver.recv_requests()
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/utils/nvtx_utils.py", line 109, in wrapper
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler_components/request_receiver.py", line 93, in recv_requests
    recv_reqs = self._broadcast_reqs_across_ranks(recv_reqs)
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler_components/request_receiver.py", line 209, in _broadcast_reqs_across_ranks
    recv_reqs = broadcast_pyobj(
                ^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/utils/common.py", line 1474, in broadcast_pyobj
    serialized_data = pickle.dumps(data)
                      ^^^^^^^^^^^^^^^^^^
TypeError: cannot pickle 'mappingproxy' object
```

### Reproduction

```bash
SGLANG_RUST_SERVER=1 sglang serve --model-path Qwen/Qwen3-235B-A22B-FP8 --tp-size 4 --port 30000 --disable-radix-cache --cuda-graph-max-bs 2048 --max-running-requests 2048 --page-size 64 --tokenizer-worker-num 8  --detokenizer-worker-num 8 
```

```
curl http://127.0.0.1:30000/generate -H "Content-Type: application/json" -d '{"text": "The capital of France is", "sampling_params":{"temperature": 0, "max_new_tokens": 200}}'
```

### Environment

N/A
