---
source_id: sglang-github-closed-issues-prs
title: '[Cherry-pick to release/v0.5.15] support GLM-5.2 MTP index sharing with prefill
  CP (#30992)'
canonical_url: https://github.com/sgl-project/sglang/pull/31106
captured_at: '2026-07-14T23:40:21.684179+00:00'
content_hash: 8c53af840d5b6de156f566686b0b4e32f10d175bf851384f3a6ba686e38f653b
---
# [Cherry-pick to release/v0.5.15] support GLM-5.2 MTP index sharing with prefill CP (#30992)

URL: https://github.com/sgl-project/sglang/pull/31106
State: closed
Labels: deepseek
Closed at: 2026-07-14T04:11:43Z
Merged at: 2026-07-14T04:11:43Z

## Summary

Manually backports the current authored changes from #30992 to `release/v0.5.15`:

- support GLM-5.2 MTP DSA index sharing with prefill context parallelism
- handle padded and expanded DSA transform-index inputs
- add kernel and 4-GPU GLM-5.2 CP coverage

This is a draft because the source PR is still open.

## Source commits

- `d46119ddb109b85a4743311f249aae8c1ded98fd`
- `cbc7fd563773b931dc309d945b7ef031ff7ed3fa`
- `2806cfe5027bce7a18505805c8749a163ccd1259`

The source branch's merge commits from `main` were intentionally excluded. Each authored commit was cherry-picked with `-x`.

## Conflict resolution

`dsa_backend.py` had one release-branch conflict. The resolution preserves the release branch's backend-aware `self.use_fused_topk` flag while applying the source change's fused/ragged/decode-specific top-k padding behavior.

## Validation

- `pre-commit run --from-ref origin/release/v0.5.15 --to-ref HEAD`
- Python compilation for all seven changed Python files
- `git diff --check origin/release/v0.5.15...HEAD`

The CUDA kernel test could not run in the local Apple Silicon environment because PyTorch, Triton, and CUDA are unavailable; the backported registered tests provide GPU CI coverage.









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29302165005](https://github.com/sgl-project/sglang/actions/runs/29302165005)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29302164957](https://github.com/sgl-project/sglang/actions/runs/29302164957)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
