---
source_id: sglang-github-closed-issues-prs
title: Fix DeepEP CI test registration
canonical_url: https://github.com/sgl-project/sglang/pull/30873
captured_at: '2026-07-12T23:38:53.055379+00:00'
content_hash: c76aaffccddc7b56e121ba83e15f376e8bac1a9e3cd5aa3095e91f50baa75029
---
# Fix DeepEP CI test registration

URL: https://github.com/sgl-project/sglang/pull/30873
State: closed
Labels: run-ci, run-ci-extra
Closed at: 2026-07-12T12:54:51Z
Merged at: 2026-07-12T12:54:51Z

## Summary

The DeepEP tests from #16859 and #28421 were running on the regular H100 config, which makes them fail on PRs where DeepEP needs to be rebuilt, so this moves them to the existing DeepEP H100 config and adds its `extra-b` job





































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29152362875](https://github.com/sgl-project/sglang/actions/runs/29152362875)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29192064506](https://github.com/sgl-project/sglang/actions/runs/29192064506)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
