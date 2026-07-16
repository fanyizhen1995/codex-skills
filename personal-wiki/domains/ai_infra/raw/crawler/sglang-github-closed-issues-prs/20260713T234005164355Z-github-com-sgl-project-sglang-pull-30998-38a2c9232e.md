---
source_id: sglang-github-closed-issues-prs
title: '[Spec] Remove dead `padded_static_len` and stale `SGLANG_ENABLE_SPEC_V2` references'
canonical_url: https://github.com/sgl-project/sglang/pull/30998
captured_at: '2026-07-13T23:40:05.164355+00:00'
content_hash: 38a2c9232e4ee7a6dae23e5170e338aa0e08c10d473dbb0ba1931386f7f3f9b7
---
# [Spec] Remove dead `padded_static_len` and stale `SGLANG_ENABLE_SPEC_V2` references

URL: https://github.com/sgl-project/sglang/pull/30998
State: closed
Labels: documentation, deepseek, npu, run-ci
Closed at: 2026-07-13T20:30:32Z
Merged at: 2026-07-13T20:30:32Z

Stacks on #30977. Two dead-residue removals from the retired spec V1 / SpecV2-flag era:

- **Remove dead `padded_static_len`**: no production writer other than the constant `-1` since the spec V1 workers were removed (#25464). The padded-indexing branch in `LogitsProcessor` is unreachable, and the `ForwardBatch` / `LogitsMetadata` fields plus the graph-runner pass-throughs are dead plumbing. The only non-`-1` writer was an attention-unittest kit whose batches never reach the logits processor.
- **Remove stale `SGLANG_ENABLE_SPEC_V2` references**: the env var was removed (spec always runs the V2 worker; the launch-time removal notice stays), but ~29 tests still set it as a no-op and `docs_new` deployment snippets still taught users to export it.































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29281901175](https://github.com/sgl-project/sglang/actions/runs/29281901175)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29281900900](https://github.com/sgl-project/sglang/actions/runs/29281900900)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
