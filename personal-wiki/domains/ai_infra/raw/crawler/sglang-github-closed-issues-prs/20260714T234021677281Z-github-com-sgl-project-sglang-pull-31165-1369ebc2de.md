---
source_id: sglang-github-closed-issues-prs
title: Drop ModelRunner's duplicated parallel-degree fields and read them via self.ps
canonical_url: https://github.com/sgl-project/sglang/pull/31165
captured_at: '2026-07-14T23:40:21.677281+00:00'
content_hash: 1369ebc2dece5a274af3c36226527b8b74d76682aa3eb725460f8f6901219c61
---
# Drop ModelRunner's duplicated parallel-degree fields and read them via self.ps

URL: https://github.com/sgl-project/sglang/pull/31165
State: closed
Labels: npu
Closed at: 2026-07-14T08:02:41Z
Merged at: 2026-07-14T08:02:40Z

ModelRunner kept self.tp_rank/tp_size/pp_*/dp_*/moe_*/attn_cp_* alongside the
ParallelState in self.ps. Remove the duplicates: build self.ps directly from the
constructor args and read every parallel rank/size through self.ps.<field> (no
property shims), updating the in-file reads and the external readers (attention
backends, eplb, expert_backup_client, spec cuda-graph runners, pool_configurator).
init_torch_distributed now reads ps.<field> directly in its body instead of
unpacking ps into locals at the top. self.gpu_id is kept (device identity, used
pervasively).







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29316613700](https://github.com/sgl-project/sglang/actions/runs/29316613700)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29316613320](https://github.com/sgl-project/sglang/actions/runs/29316613320)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
