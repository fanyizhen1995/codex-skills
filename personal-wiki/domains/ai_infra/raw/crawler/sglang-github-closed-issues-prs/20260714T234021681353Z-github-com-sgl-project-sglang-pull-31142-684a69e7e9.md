---
source_id: sglang-github-closed-issues-prs
title: Clarify ModelRunner.dp_size into attn_dp_size
canonical_url: https://github.com/sgl-project/sglang/pull/31142
captured_at: '2026-07-14T23:40:21.681353+00:00'
content_hash: 684a69e7e98493fb913430498fe990dcb54414d0e7c9e87666f4f375a88eea26
---
# Clarify ModelRunner.dp_size into attn_dp_size

URL: https://github.com/sgl-project/sglang/pull/31142
State: closed
Labels: 
Closed at: 2026-07-14T07:49:06Z
Merged at: 2026-07-14T07:49:06Z

Also rename the consumer-side fields that mirror it: the EAGLE draft /
draft-extend / frozen-KV-MTP cuda-graph runners' own dp_size fields
(assigned from ModelRunner.attn_dp_size) become attn_dp_size, together
with their in-class uses.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29315641562](https://github.com/sgl-project/sglang/actions/runs/29315641562)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29315641360](https://github.com/sgl-project/sglang/actions/runs/29315641360)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
