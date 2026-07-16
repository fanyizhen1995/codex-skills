---
source_id: sglang-github-closed-issues-prs
title: Sanitize exception messages in HTTP error responses (#18348)
canonical_url: https://github.com/sgl-project/sglang/pull/19861
captured_at: '2026-07-13T23:40:05.172951+00:00'
content_hash: 556c11cc5c08df98931fc508a812ec91e77fd8c9c11a583659ea4c1a3da6a275
---
# Sanitize exception messages in HTTP error responses (#18348)

URL: https://github.com/sgl-project/sglang/pull/19861
State: closed
Labels: 
Closed at: 2026-07-13T18:39:43Z
Merged at: 

## Summary

Exception messages in HTTP responses can leak internal details. Added centralized error sanitization with error_id correlation, with opt-in --enable-debug-error-responses flag for development.

Closes #18348
