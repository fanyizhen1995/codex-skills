---
source_id: sglang-github-closed-issues-prs
title: Fix streaming delta emitting role:null, content:null (#18335)
canonical_url: https://github.com/sgl-project/sglang/pull/19858
captured_at: '2026-07-13T23:40:05.171792+00:00'
content_hash: d071765b3ce9729b6a3fb71f45b7b96acf0223e4579789cb048cab5c38db2574
---
# Fix streaming delta emitting role:null, content:null (#18335)

URL: https://github.com/sgl-project/sglang/pull/19858
State: closed
Labels: 
Closed at: 2026-07-13T18:39:46Z
Merged at: 

## Summary
`DeltaMessage._serialize` was including None-valued fields in the serialized output, causing streaming chunks to emit `role: null, content: null` which breaks OpenAI-compatible clients. Fixed by filtering out None fields. Closes #18335
