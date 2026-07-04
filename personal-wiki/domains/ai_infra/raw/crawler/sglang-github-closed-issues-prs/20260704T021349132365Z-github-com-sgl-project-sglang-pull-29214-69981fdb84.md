---
source_id: sglang-github-closed-issues-prs
title: '[Cleanup] IPC struct renames, better typing, and SenderWrapper removal'
canonical_url: https://github.com/sgl-project/sglang/pull/29214
captured_at: '2026-07-04T02:13:49.132365+00:00'
content_hash: 69981fdb8471ee33e96fe3061929b9db9b0aa4f22c8ae8178ef7ebe5cde6b7d6
---
# [Cleanup] IPC struct renames, better typing, and SenderWrapper removal

URL: https://github.com/sgl-project/sglang/pull/29214
State: closed
Labels: npu, run-ci
Closed at: 2026-06-25T00:25:24Z
Merged at: 2026-06-25T00:25:24Z

## Summary

Preparatory cleanup extracted from #28688 (IPC msgspec migration), containing only the non-serialization-related changes. This PR makes it easier to review the msgspec migration separately.

- Delete `SenderWrapper`; replace with `stamp_http_worker_ipc()` and `_dispatch_to_scheduler()`/`_async_dispatch_to_scheduler()` methods
- Rename `TokenizerWorkerRegistration` → `TokenizerWorkerRegistrationReq`, `PauseContinueBroadcast` → `PauseContinueBroadcastReq`, `BlockReqInput.type` → `BlockReqInput.req_type`, `TokenizedEmbeddingReqInput.image_inputs` → `mm_inputs`
- Add type aliases (`FinishReasonDict`, `CachedTokensDetails`, `TokenLogprobValues`, `TopLogprobValues`, `OutputHiddenStates`)
- Remove `SpeculativeDecodingMetricsMixin`; inline fields into output classes
- Remove deprecated `data_parallel_rank` field and migration code
- Move `regenerate_rid`/`_validate_rid_uniqueness` to concrete classes (`GenerateReqInput`, `EmbeddingReqInput`)
- Wrap FastAPI body params with `Annotated[..., Body()]`
- Replace `getattr()` calls with direct attribute access
- Simplify `PositionalEmbeds.embeds` type to `torch.Tensor`
- `FanOutCommunicator` now takes a `Callable` instead of a raw socket
- Reorder fields for consistency across request types

## Test plan
- [ ] CI passes (no functional changes, only renames/typing/refactors)
- [ ] Verify existing tests still pass with renamed structs

Co-authored-by: Rain Jiang <96632942+rainj-me@users.noreply.github.com>











































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28135707747](https://github.com/sgl-project/sglang/actions/runs/28135707747)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28135707620](https://github.com/sgl-project/sglang/actions/runs/28135707620)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
