---
source_id: sglang-github-closed-issues-prs
title: Fix rel_diff being nan for bitwise-identical tensors
canonical_url: https://github.com/sgl-project/sglang/pull/30655
captured_at: '2026-07-09T23:36:35.329189+00:00'
content_hash: 7ed1f618ab3a31826922935d4d086c7c26e2d745521ac8e48a4bae53fe609c2f
---
# Fix rel_diff being nan for bitwise-identical tensors

URL: https://github.com/sgl-project/sglang/pull/30655
State: closed
Labels: 
Closed at: 2026-07-09T12:16:19Z
Merged at: 2026-07-09T12:16:19Z

calc_rel_diff on two bitwise-identical tensors evaluates 0/0 and returns NaN.
Any comparison against NaN is False, so under the predicate DSL a strict
'rel <= 0' criterion (exact-match checking, e.g. deterministic-mode dumps)
spuriously fails precisely on the tensors that match perfectly - including
legitimate all-zero tensors such as grads of starved MoE experts.

A zero max_abs_diff means the tensors are identical, so define their relative
diff as 0.0 instead of computing the 0/0 ratio. Reported rel_diff for identical
tensors changes from NaN to 0.0 accordingly.

Add a regression test: 'rel <= 0' passes for a tensor compared against its
clone and still fails for a sign-flipped near-zero pair.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29017579580](https://github.com/sgl-project/sglang/actions/runs/29017579580)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29017579511](https://github.com/sgl-project/sglang/actions/runs/29017579511)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
