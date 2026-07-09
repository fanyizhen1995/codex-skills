---
source_id: sglang-github-closed-issues-prs
title: 'feat(grpc): support disaggregated generation requests'
canonical_url: https://github.com/sgl-project/sglang/pull/30440
captured_at: '2026-07-08T23:36:33.787928+00:00'
content_hash: fc563556cf5d52cce72a735885f077737c9f0540bd6b796ef1573d9fc70e2931
---
# feat(grpc): support disaggregated generation requests

URL: https://github.com/sgl-project/sglang/pull/30440
State: closed
Labels: run-ci
Closed at: 2026-07-08T21:53:57Z
Merged at: 2026-07-08T21:53:57Z

## Summary

- add `DisaggregatedParams` to the native `sglang.runtime.v1` contract
- expose the rendezvous parameters on both `Generate` and `TextGenerate`
- forward `bootstrap_host`, `bootstrap_port`, and `bootstrap_room` into `GenerateReqInput`
- preserve full signed 64-bit room IDs and omit the fields for aggregated requests

This includes the protobuf work from #25185 and adds the server-side handling needed for native-gRPC prefill/decode disaggregation.

## Root cause

The native gRPC contract could carry the rendezvous tuple after #25185, but the Rust request bridge did not copy it into the top-level `GenerateReqInput` fields used by SGLang's disaggregation path. As a result, clients such as Dynamo could populate the protobuf while the prefill and decode workers still received no bootstrap identity.

## Validation

- `cargo fmt --check`
- `cargo test` — 10 passed
- `cargo clippy --all-targets -- -D warnings -A clippy::let-underscore-future`


















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28906605180](https://github.com/sgl-project/sglang/actions/runs/28906605180)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28906605091](https://github.com/sgl-project/sglang/actions/runs/28906605091)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
