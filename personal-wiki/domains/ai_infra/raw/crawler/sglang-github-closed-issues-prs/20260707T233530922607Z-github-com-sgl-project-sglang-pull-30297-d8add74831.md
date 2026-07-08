---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Resolve config declarations onto server_args at the end of __post_init__'
canonical_url: https://github.com/sgl-project/sglang/pull/30297
captured_at: '2026-07-07T23:35:30.922607+00:00'
content_hash: d8add74831609b2260ca35dff23850d9ef0360c4d74f2325326cd3c8f89d3d38
---
# [refactor] Resolve config declarations onto server_args at the end of __post_init__

URL: https://github.com/sgl-project/sglang/pull/30297
State: closed
Labels: deepseek, speculative-decoding, run-ci, bypass-fastfail, run-ci-extra
Closed at: 2026-07-07T01:04:45Z
Merged at: 2026-07-07T01:04:45Z

Continues the config-resolution pipeline series (#30063–#30077, #30137); supersedes the retirement stack #30228–#30232 (closed unmerged).

The resolution pipeline keeps declaring — registry dispatch, post-process passes, provenance stash — but no longer replays each declaration in place. Instead, `__post_init__` applies the accumulated stash onto the fields once, at its very end (gate order, last writer wins).

**Developer contract:** after `__post_init__` returns, `server_args` carries the resolved configuration — read the fields directly, in any process. The read-only pass view is internal to the resolution pipeline: only mid-resolution code in `server_args.py` / `arg_groups/` touches it. No new read API is exposed to the rest of the codebase; every runtime file reads exactly as it does today.

During resolution the fields stay untouched: the handler chains, the speculative / hisparse hooks, the adaptive-spec gate and the validation blocks (converted to read-only passes) observe the declared-so-far state through views, so the write-in-place era's slot-ordering hazards — a later imperative write shadowed by an earlier declaration, or a reader observing a half-applied state — cannot recur. Passes invoked after materialization (runtime slots) and `declare_load_time_override` write through immediately; publish keeps asserting parity between the fields and the flag leaves. The pristine user input remains recoverable from the provenance records.

Also carried at their legacy slots: the runner-fusion and a2a-fusion writes converted to declarations, the Qwen3.5 hybrid dispatch reading the mamba strategy declared by the earlier mamba slot, and the dllm page cap invoked outside the radix gate (replacing the unconditional scheduler-init fallback). These fold in the review findings from the superseded stack.

11 files, main+1 commit.

🤖 Generated with [Claude Code](https://claude.com/claude-code)











































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28824161565](https://github.com/sgl-project/sglang/actions/runs/28824161565)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28824161448](https://github.com/sgl-project/sglang/actions/runs/28824161448)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
