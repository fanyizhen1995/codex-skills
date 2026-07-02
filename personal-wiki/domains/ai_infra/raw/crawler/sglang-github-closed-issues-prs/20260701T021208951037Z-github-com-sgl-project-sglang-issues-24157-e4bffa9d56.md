---
source_id: sglang-github-closed-issues-prs
title: '[Feature] Thread endpoint_url through S3Connector for S3-compatible providers
  (Backblaze B2)'
canonical_url: https://github.com/sgl-project/sglang/issues/24157
captured_at: '2026-07-01T02:12:08.951037+00:00'
content_hash: e4bffa9d564f47f7adddba9309fefde5401de0ad7fdf900223a865d104e3daad
---
# [Feature] Thread endpoint_url through S3Connector for S3-compatible providers (Backblaze B2)

URL: https://github.com/sgl-project/sglang/issues/24157
State: closed
Labels: inactive
Closed at: 2026-06-30T00:48:49Z
Merged at: 

### Checklist

- [x] If this is not a feature request but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Motivation

`python/sglang/srt/connector/s3.py` builds the boto3 client without `endpoint_url`/`region`/credential kwargs, so S3-compatible providers (Backblaze B2) only work via `AWS_ENDPOINT_URL` env var. 

Steps: 
1. Accept `endpoint_url`, `region_name`, key kwargs on `S3Connector.__init__`. Parse from URI query string (`s3://bucket/path?endpoint_url=...`) or fall back to env.
2. Pass through to `boto3.client("s3", ...)`.
3. Add basic testing
4. Update paragraphs in documentation.

I have a draft [branch ready](https://github.com/sgl-project/sglang/compare/main...goanpeca:feat/s3-endpoint-url?expand=1) and can submit the PR.

### Related resources

- vLLM weight-loader endpoint_url plumbing (precedent).
- Backblaze B2 S3 docs: https://www.backblaze.com/b2/docs/s3_compatible_api.html
