---
source_id: sglang-github-closed-issues-prs
title: Fix hashtopk empty return annotation
canonical_url: https://github.com/sgl-project/sglang/pull/30941
captured_at: '2026-07-12T23:38:53.054892+00:00'
content_hash: 2d2fc078b94cb9015dcd40493173a774ed51a4f1911440a8be7fb892a7fe05fd
---
# Fix hashtopk empty return annotation

URL: https://github.com/sgl-project/sglang/pull/30941
State: closed
Labels: 
Closed at: 2026-07-12T18:16:39Z
Merged at: 

## Motivation

Address the `gemini-code-assist` review comment on sgl-project/sglang#30939 by adding the missing return type annotation to `HashTopK.empty_topk_output`.

## Modifications

- Add `-> StandardTopKOutput` to `HashTopK.empty_topk_output`.
This PR is intended as a small helper PR into `glaziermag:agent/fix-hash-topk-empty-output` so the commit can be cherry-picked into sgl-project/sglang#30939.

Commit to cherry-pick: `7867e6b621b68d079a60657128a0b932a23901f5`

## Accuracy Tests

Not applicable.

## Speed Tests and Profiling

Not applicable. 







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29203264315](https://github.com/sgl-project/sglang/actions/runs/29203264315)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29203264283](https://github.com/sgl-project/sglang/actions/runs/29203264283)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
