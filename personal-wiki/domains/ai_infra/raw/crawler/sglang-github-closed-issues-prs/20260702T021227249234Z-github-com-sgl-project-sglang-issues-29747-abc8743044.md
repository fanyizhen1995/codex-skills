---
source_id: sglang-github-closed-issues-prs
title: '[Bug] I''d like to know if it''s possible to deploy Deepseek-v4-flash on a
  4090.'
canonical_url: https://github.com/sgl-project/sglang/issues/29747
captured_at: '2026-07-02T02:12:27.249234+00:00'
content_hash: abc874304494361b1031ea6d64f716ca0965251cbc7a4a84e4f76221ffe704d8
---
# [Bug] I'd like to know if it's possible to deploy Deepseek-v4-flash on a 4090.

URL: https://github.com/sgl-project/sglang/issues/29747
State: closed
Labels: 
Closed at: 2026-07-01T08:45:15Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

Encounter the problem shown in the screenshot (please forgive me for only being able to use a screenshot, as this machine cannot copy content).

<img width="1362" height="909" alt="Image" src="https://github.com/user-attachments/assets/7fdd7f37-4ca2-497b-8b05-f4f7c9ecc375" />

I'm deploying it on 8*RTX 4090s with 48GB of RAM. I can add any further information if needed.


### Reproduction

```
docker run \
-d \
--gpus all \
--shm-size=256g \
--name sgl-ds-v4 \
--network=host \
-v /llm/hub/deepseek/DeepSeek-V4-Flash:/model \
-e NCCL_P2P_DISABLE=1 \
-e NCCL_IB_DISABLE=1 \
-e NCCL_TIMEOUT=300000 \
-e NCCL_BUFFSIZE=33554432 \
-e NCCL_MAX_NCHANNELS=8 \
-e CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
lmsysorg/sglang:dev-cu12 \
sglang serve \
--model-path /model \
--tp 8 \
--host 0.0.0.0 \
--port 30000 \
--trust-remote-code \
--mem-fraction-static 0.52 \
--cuda-graph-max-bs-decode 16 \
--cuda-graph-backend-decode disabled \
--cuda-graph-backend-prefill disabled \
--attention-backend flashmla \
--context-length 500000
```

### Environment

As above, I can't copy the content, but I'm using Docker, so the environment should be reproducible.
