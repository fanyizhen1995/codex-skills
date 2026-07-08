---
source_id: sglang-github-closed-issues-prs
title: '[Feature] [GLM5.2] Index share reuse with MHA'
canonical_url: https://github.com/sgl-project/sglang/issues/29951
captured_at: '2026-07-05T02:14:10.234167+00:00'
content_hash: b7be0d63762972d6f6a0c18db7b90265ede94d5b8c9ed9bd9fe9ea3b14f6b411
---
# [Feature] [GLM5.2] Index share reuse with MHA

URL: https://github.com/sgl-project/sglang/issues/29951
State: closed
Labels: 
Closed at: 2026-07-04T09:50:28Z
Merged at: 

### Checklist

- [x] If this is not a feature request but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Motivation

When prefill runs with MHA (no CUDA graphs), the DSA indexer is called on every layer (with skip-topk for MHA), whereas with Index Share there's no need to manipulate the K cache on shared layers.

<img width="3440" height="947" alt="Image" src="https://github.com/user-attachments/assets/bb21a104-52ba-4e2d-a6af-e6f304dff3af" />

During CUDA graph execution (BCG / decode), the DSA indexer is skipped for shared layers (as MLA is forced).

### Related resources

_No response_
