---
source_id: sglang-github-closed-issues-prs
title: '[misc] Add CI-only guards for the FutureMap seq_lens relay'
canonical_url: https://github.com/sgl-project/sglang/pull/30471
captured_at: '2026-07-08T23:36:33.787459+00:00'
content_hash: 7acfb673516305cd3ef577533c44b470448f33746e2870ce8fa27130e9f47709
---
# [misc] Add CI-only guards for the FutureMap seq_lens relay

URL: https://github.com/sgl-project/sglang/pull/30471
State: closed
Labels: run-ci
Closed at: 2026-07-08T22:29:53Z
Merged at: 2026-07-08T22:29:53Z

CI-only (`SGLANG_IS_IN_CI`) guards for the seq_lens relay protocol, one per plane: a consume-once assert on `publish_ready` (sync plane: every resolve must be re-armed by a fresh forward publish) and -1 poisoning of consumed `new_seq_lens_buf` rows (data plane: every row must be re-published/seeded before its next gather). Zero cost outside CI. Stacks on #30435.









































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28974588078](https://github.com/sgl-project/sglang/actions/runs/28974588078)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28974587802](https://github.com/sgl-project/sglang/actions/runs/28974587802)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
