---
source_id: sglang-github-closed-issues-prs
title: '[Feature] DP attn: We should fuse global_tokens.fill_(0) and memcpy_triton()
  into one kernel'
canonical_url: https://github.com/sgl-project/sglang/issues/24938
captured_at: '2026-07-11T23:37:37.765204+00:00'
content_hash: 32ec2e19237e0c38d2537831227cb08fe994f593f2f7e901b10e968b65dbc397
---
# [Feature] DP attn: We should fuse global_tokens.fill_(0) and memcpy_triton() into one kernel

URL: https://github.com/sgl-project/sglang/issues/24938
State: closed
Labels: inactive
Closed at: 2026-07-11T00:32:58Z
Merged at: 

### Checklist

- [ ] If this is not a feature request but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [ ] Please use English. Otherwise, it will be closed.

### Motivation

- https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/layers/dp_attention.py#L463
- https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/layers/dp_attention.py#L559

Both fill_ and memcpy are HBM bandwidth bound for the same tensor object so we should fuse them

### Related resources

_No response_
