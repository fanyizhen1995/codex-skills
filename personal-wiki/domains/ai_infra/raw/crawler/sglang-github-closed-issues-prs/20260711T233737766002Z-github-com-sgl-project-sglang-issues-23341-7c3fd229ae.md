---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Kimi-K2 tool parser streaming content dropping'
canonical_url: https://github.com/sgl-project/sglang/issues/23341
captured_at: '2026-07-11T23:37:37.766002+00:00'
content_hash: 7c3fd229aef1de143faae508d9e14b87f775732407db6a6ab3492a55beb8b5ea
---
# [Bug] Kimi-K2 tool parser streaming content dropping

URL: https://github.com/sgl-project/sglang/issues/23341
State: closed
Labels: inactive
Closed at: 2026-07-11T00:32:54Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

When I used my test script to test the function_call accuracy of kimi-k2.5, I found an issue: max_tokens=16k, but the response output content is empty, and finish_reason = stop.

### Reproduction

 Below is a simple reproduction script.


[test_eos_qoder.py](https://github.com/user-attachments/files/26923499/test_eos_qoder.py)
simple test: `python test_eos_qoder.py  --endpoint http://localhost:30000/v1/chat/completions --api-key xxx`

--------my result---------
```
D:\otherPrograms\anaconda3\envs\py312\python.exe D:\workspace\ai-tools-scripts\kimi-k2.5\test_eos_qoder.py 
============================================================
K2.5 EOS Test Script for Qoder Dataset (qoder_0001)
============================================================
Endpoint: https://xxxxxxx/v1/chat/completions
Requests: 1000
Workers: 100
Timeout: 300s

Health check: 404

Sending 1000 requests to https://xxxxxx/v1/chat/completions
Using 100 concurrent workers
------------------------------------------------------------
Testing: 100%|██████████| 1000/1000 [01:56<00:00,  8.59it/s]

============================================================
TEST RESULTS
============================================================

Total requests: 1000
Successful: 1000
Failed: 0

--- Finish Reason Distribution ---
  stop: 928 (92.8%)
  tool_calls: 72 (7.2%)

============================================================
K2.5 EOS TEST SUMMARY
============================================================
In finish_reason = stop 的 928  response 中,
有 840 条 content 为空, 比例为 90.52%

--- Latency Statistics ---
  Min: 1533 ms
  Max: 18844 ms
  Avg: 11201 ms

进程已结束，退出代码为 0

```

### Environment

image: sglang:v0.5.10-cu130
model: kimi-k2.5 FP8
