---
source_id: sglang-github-closed-issues-prs
title: Clean up ModelRunner by renaming effective-token property and remove dead code
canonical_url: https://github.com/sgl-project/sglang/pull/31145
captured_at: '2026-07-14T23:40:21.681127+00:00'
content_hash: 0c9272de77b794a3533eaa070264e92abed0b9677161af90cd59bd483f96c0f9
---
# Clean up ModelRunner by renaming effective-token property and remove dead code

URL: https://github.com/sgl-project/sglang/pull/31145
State: closed
Labels: 
Closed at: 2026-07-14T07:50:54Z
Merged at: 2026-07-14T07:50:53Z

### mrc-misc-cleanups(effective-max-total-num-tokens,non_mechanical_provable): Rename the max_token_pool_size property to effective_max_total_num_tokens and route prefill/tp_worker through it

### mrc-misc-cleanups(remove-unused-mla-attention-backends,non_mechanical_provable): Remove unused MLA_ATTENTION_BACKENDS and add_mla_attention_backend

Both the MLA_ATTENTION_BACKENDS list and its add_mla_attention_backend
mutator had no readers anywhere under python/sglang/srt (only the
definition existed). Delete the dead pair.

### mrc-misc-cleanups(drop-vestigial-alloc-memory-pool-defaults,non_mechanical_provable): Drop vestigial backend/graph None-defaults from alloc_memory_pool

The six self.attn_backend / decode_attn_backend / decode_attn_backend_group /
decode_cuda_graph_runner / graph_mem_usage / prefill_cuda_graph_runner = None defaults
at the end of alloc_memory_pool were a leftover fallback for an old
disable_cuda_graph early-skip path. init_model_worker now unconditionally calls
init_attention_backends (assigns the attn trio) and init_cuda_graphs (assigns the
cuda-graph trio, always returning all fields even when capture is disabled), both
before any forward, and nothing probes these fields with hasattr/getattr. Remove the
dead defaults.

### mrc-misc-cleanups(drop-rank-zero-filter,non_mechanical_provable): Remove unused RankZeroFilter class from model_runner.py











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29315896354](https://github.com/sgl-project/sglang/actions/runs/29315896354)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29315896240](https://github.com/sgl-project/sglang/actions/runs/29315896240)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
