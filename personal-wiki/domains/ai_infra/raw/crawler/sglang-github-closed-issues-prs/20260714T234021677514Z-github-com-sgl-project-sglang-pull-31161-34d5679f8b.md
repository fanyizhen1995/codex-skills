---
source_id: sglang-github-closed-issues-prs
title: Introduce ModelRunner.ps ParallelState
canonical_url: https://github.com/sgl-project/sglang/pull/31161
captured_at: '2026-07-14T23:40:21.677514+00:00'
content_hash: 34d5679f8b991e00286bc4489caeb3459916717a05418ee027a49be8a3e715c5
---
# Introduce ModelRunner.ps ParallelState

URL: https://github.com/sgl-project/sglang/pull/31161
State: closed
Labels: Multi-modal, apple-silicon
Closed at: 2026-07-14T08:01:14Z
Merged at: 2026-07-14T08:01:14Z

Mirror Scheduler.ps: build a ParallelState in ModelRunner.__init__ (full 17 fields; attn_tp/attn_dp via compute_dp_attention_world_info, the rest from ModelRunner's own self.* values) and pass self.ps to init_torch_distributed instead of nine separate rank/size args. init_torch_distributed now takes ps and unpacks it to locals at the top, body unchanged. self.tp_rank etc. are kept for the many in-file reads.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29316536700](https://github.com/sgl-project/sglang/actions/runs/29316536700)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29316536415](https://github.com/sgl-project/sglang/actions/runs/29316536415)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
