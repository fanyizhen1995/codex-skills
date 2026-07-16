---
source_id: sglang-github-closed-issues-prs
title: Split initialize() into orchestration helpers
canonical_url: https://github.com/sgl-project/sglang/pull/31169
captured_at: '2026-07-14T23:40:21.674826+00:00'
content_hash: 4ab48c6d148277d681aa88602bd008ebaa8a0748279ffbe6aee9e328b74b3b77
---
# Split initialize() into orchestration helpers

URL: https://github.com/sgl-project/sglang/pull/31169
State: closed
Labels: run-ci
Closed at: 2026-07-14T08:09:01Z
Merged at: 2026-07-14T08:09:01Z

### mrc-init-orchestration(maybe-recover-ep-ranks-prep,non_mechanical_provable): Stage maybe_recover_ep_ranks / maybe_rebalance_after_rank_fault as de-self'd free functions at the model_runner tail and rewire callers (forward_pass_id write lifted to caller)

### mrc-init-orchestration(maybe-recover-ep-ranks-move,mechanical_provable): Move maybe_recover_ep_ranks + rebroadcast_expert_location_metadata to elastic_ep.py (cut+paste)

### mrc-init-orchestration(initialize-init-helpers,non_mechanical_provable): Split initialize() into init_* orchestration helpers

Restructure ModelRunner.initialize() into a sequence of self.init_* /
self.maybe_init_* override points per the large-class init style: memory-saver
adapter, remote-instance transfer engine, expert-location metadata, lplb
solvers, eplb manager, elastic EP, token oracle, expert backup client,
post-load model transforms, lora manager, batch-invariant mode, and the
hisparse coordinator.









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29316767629](https://github.com/sgl-project/sglang/actions/runs/29316767629)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29316767270](https://github.com/sgl-project/sglang/actions/runs/29316767270)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
