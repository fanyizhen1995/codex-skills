---
source_id: sglang-github-closed-issues-prs
title: Support real draft tokens to simulated acceptance
canonical_url: https://github.com/sgl-project/sglang/pull/29645
captured_at: '2026-07-01T02:12:08.953224+00:00'
content_hash: ba7595f2fca039811af9adac58d07dbfb9e0b7ffcd5b4b47f34aab61ad46ab27
---
# Support real draft tokens to simulated acceptance

URL: https://github.com/sgl-project/sglang/pull/29645
State: closed
Labels: run-ci
Closed at: 2026-07-01T00:22:06Z
Merged at: 2026-07-01T00:22:05Z

## Summary

- add `SGLANG_SIMULATE_ACC_TOKEN_MODE` with `fixed` and `real-draft-token` modes
- preserve the legacy `predict.fill_(100)` simulation behavior by default, including tree top-k greater than one
- allow top-k=1 simulations to opt into real draft-chain tokens with a target-derived terminal bonus

## Motivation

`SGLANG_SIMULATE_ACC_LEN` changes acceptance metadata after normal verification and historically fills the prediction buffer with token ID 100. Although ID 100 is numerically inside the DeepSeek-V4 vocabulary, it is not necessarily the verified token for the selected draft path. The fabricated token ID can therefore be paired with KV state produced for different draft tokens, making downstream decode consume inconsistent token/cache state.

Some performance benchmarks rely on the existing fixed-token behavior, so this change keeps it as the default rather than changing established simulation semantics. Users that need token/KV-coherent output can opt into the real top-k=1 draft path.

## Usage

The default remains the legacy fixed-token mode:

```bash
export SGLANG_SIMULATE_ACC_TOKEN_MODE=fixed
```

To use the real draft prefix and a target-derived terminal token:

```bash
export SGLANG_SIMULATE_ACC_TOKEN_MODE=real-draft-token
```

`real-draft-token` requires `speculative_eagle_topk=1`. The default `fixed` mode retains the previous top-k behavior.

## Validation

- top-k=1 end-to-end generation with a small Qwen3.5 model, confirming expected simulated acceptance lengths, coherent output, and no fabricated token 100 in accepted output
- verified the environment variable defaults to `fixed` and parses `real-draft-token`
- Ruff, Black, isort, Python compile checks, registered-test validation, and `git diff --check`











































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28480746560](https://github.com/sgl-project/sglang/actions/runs/28480746560)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28480746422](https://github.com/sgl-project/sglang/actions/runs/28480746422)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
