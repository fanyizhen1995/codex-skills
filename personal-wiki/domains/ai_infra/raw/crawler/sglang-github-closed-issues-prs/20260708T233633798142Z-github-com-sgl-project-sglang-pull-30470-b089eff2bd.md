---
source_id: sglang-github-closed-issues-prs
title: '[misc] Add CI-only guards for the FutureMap seq_lens relay'
canonical_url: https://github.com/sgl-project/sglang/pull/30470
captured_at: '2026-07-08T23:36:33.798142+00:00'
content_hash: b089eff2bd894fb363fec417ac24aeb338afc624e123daf1f07a7b7dbe58a6b5
---
# [misc] Add CI-only guards for the FutureMap seq_lens relay

URL: https://github.com/sgl-project/sglang/pull/30470
State: closed
Labels: 
Closed at: 2026-07-08T04:37:16Z
Merged at: 

CI-only (`SGLANG_IS_IN_CI`) guards for the seq_lens relay protocol, one per plane: a consume-once assert on `publish_ready` (sync plane: every resolve must be re-armed by a fresh forward publish) and -1 poisoning of consumed `new_seq_lens_buf` rows (data plane: every row must be re-published/seeded before its next gather). Zero cost outside CI. Stacks on #30435.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28917837494](https://github.com/sgl-project/sglang/actions/runs/28917837494)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28917837426](https://github.com/sgl-project/sglang/actions/runs/28917837426)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
