---
source_id: sglang-github-closed-issues-prs
title: 'fix: avoid double KV release on disaggregated prefill grammar errors'
canonical_url: https://github.com/sgl-project/sglang/pull/30937
captured_at: '2026-07-14T23:40:21.672422+00:00'
content_hash: a4f4371f5cf8b7229910846b7b17106f96f51e3119ae4ca675f25c8f6b4ab2b3
---
# fix: avoid double KV release on disaggregated prefill grammar errors

URL: https://github.com/sgl-project/sglang/pull/30937
State: closed
Labels: 
Closed at: 2026-07-14T12:16:59Z
Merged at: 2026-07-14T12:16:59Z

## Motivation

When grammar validation fails after a disaggregated prefill KV transfer has started, the request remains in the inflight queue until the transfer reaches a terminal state. Releasing its KV cache immediately can release the same allocation again during terminal cleanup. Terminal handling can also replace the original grammar error with a transfer result.

## Modifications

- Defer KV cache release after grammar rejection until the inflight transfer reaches a terminal state.
- Preserve an existing grammar abort reason during successful and failed transfer cleanup.
- Add CPU unit coverage for transferring, successful, and failed poll states, plus deferred external abort behavior.

## Accuracy Tests

Not applicable. This change only affects cleanup after grammar validation rejects a token.

## Speed Tests and Profiling

Not applicable. The normal inference path is unchanged.

## Checklist

- [x] Format code with pre-commit.
- [x] Add unit tests.
- [x] Documentation is not required because there are no user-facing API changes.
- [x] Accuracy and speed benchmarks are not applicable to this error-path cleanup.
- [x] Follow the SGLang code style guidance.

## Review and Merge Process

1. Get approvals from CODEOWNERS and other reviewers.
2. Trigger the required CI tests.
3. Merge after CI and required approvals are complete.















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29323853939](https://github.com/sgl-project/sglang/actions/runs/29323853939)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29323853715](https://github.com/sgl-project/sglang/actions/runs/29323853715)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
