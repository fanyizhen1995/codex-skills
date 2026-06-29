---
source_id: sglang-github-closed-issues-prs
title: 'feat: first-class session identity in SGLang'
canonical_url: https://github.com/sgl-project/sglang/pull/29436
captured_at: '2026-06-29T04:09:41.031934+00:00'
content_hash: 073f666ec5e673402030f68a94e50faf643d204f6e977f68b7521d3f62bfb0e5
---
# feat: first-class session identity in SGLang

URL: https://github.com/sgl-project/sglang/pull/29436
State: closed
Labels: run-ci, run-ci-extra
Closed at: 2026-06-28T14:16:39Z
Merged at: 2026-06-28T14:16:39Z

Adds a scalar top-level `session_id` as stable request identity and wires it through native, Engine, OpenAI, Responses, and gRPC entry points. This keeps continual-prompt `session_params` unchanged while letting the existing session radix cache use `session_id` without requiring `/open_session`.

### How This Was Implemented

- Keep `session_params` on the existing opened `SessionController` path.
- Use top-level `session_id` as the sole identity for radix-session tagging when `--enable-session-radix-cache` is enabled.
- Keep cache policy gated in the cache, so carrying identity alone does not activate session-radix behavior.
- Separate radix release from the legacy/streaming `release_session` hook.

<details>
<summary>Walkthrough</summary>

- Request adapters pass the scalar `session_id` through tokenization into `Req`.
- The scheduler routes `session_params` and `session_id` independently and rejects native requests that set both.
- Radix sessions begin implicitly on first use and release tagged KV through `/close_session`; legacy sessions retain `/open_session` semantics.

</details>

### Validation

- `247 passed, 25 subtests passed` across request normalization, OpenAI adapters, session caches, and server arguments.
- Rust gRPC request mapping test passes.
- Repository pre-commit checks and protobuf validation pass.
- Live Llama 3.2 1B: radix sessions worked without open, reused 11 cached tokens, and reclaimed tagged KV on close.
- On the same flag-enabled server, `/open_session` plus `session_params` continued through `SessionController` and closed independently.







































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28286432222](https://github.com/sgl-project/sglang/actions/runs/28286432222)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28286432136](https://github.com/sgl-project/sglang/actions/runs/28286432136)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
