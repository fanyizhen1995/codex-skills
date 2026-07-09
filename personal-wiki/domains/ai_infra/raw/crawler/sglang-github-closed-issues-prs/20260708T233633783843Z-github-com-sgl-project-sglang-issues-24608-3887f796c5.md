---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Model Gateway does not support continuous_usage_stat parameter in streaming
  generation'
canonical_url: https://github.com/sgl-project/sglang/issues/24608
captured_at: '2026-07-08T23:36:33.783843+00:00'
content_hash: 3887f796c5e384a11affc323bd165162a9f9d436c0816501e3f716c87ab46a80
---
# [Bug] Model Gateway does not support continuous_usage_stat parameter in streaming generation

URL: https://github.com/sgl-project/sglang/issues/24608
State: closed
Labels: inactive
Closed at: 2026-07-08T00:34:32Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

When using the router, adding

```json
"stream_options": {
  "include_usage": true,
  "continuous_usage_stats": true
}
```

in request does not work as expected. `continuous_usage_stats` means that each chunk should contain a usage message, but the reply still produces only the final usage chunk at the end of the stream. Sending requests with `continuous_usage_stats` to worker directly works, so the issue appears to be in the router layer.

### Reproduction

When
```
curl http://<worker>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
  "model": "model",
    "messages": [
      {"role": "user", "content": "Hello"}
    ],
    "stream": true,
    "stream_options": {
      "include_usage": true,
      "continuous_usage_stats": true
    }
  }'
```

<img width="1728" height="866" alt="Image" src="https://github.com/user-attachments/assets/1537d3a3-e05e-4ca2-b5d4-bf9b235e71c3" />

each chunk would includes a usage message, but
```
curl http://<router>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
  "model": "model",
    "messages": [
      {"role": "user", "content": "Hello"}
    ],
    "stream": true,
    "stream_options": {
      "include_usage": true,
      "continuous_usage_stats": true
    }
  }'
```
does not.

<img width="1714" height="776" alt="Image" src="https://github.com/user-attachments/assets/090ca1c9-631a-4083-ba8d-1c638eac010e" />

### Environment

can be reproduced in the latest sglang
