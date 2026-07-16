---
source_id: sglang-github-closed-issues-prs
title: Support abort_request in the router (#6531)
canonical_url: https://github.com/sgl-project/sglang/pull/20160
captured_at: '2026-07-13T23:40:05.173535+00:00'
content_hash: ae7abc29e02135cb9bd97da78ef5095175f024da228fd5fb2571e4f135f907f5
---
# Support abort_request in the router (#6531)

URL: https://github.com/sgl-project/sglang/pull/20160
State: closed
Labels: model-gateway
Closed at: 2026-07-13T18:39:42Z
Merged at: 

Adds `/abort_request` POST endpoint to the Rust router, fans out to all workers in parallel.

Closes #6531
