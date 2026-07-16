---
source_id: sglang-github-closed-issues-prs
title: Absorb capturer setup and extract the shared-mooncake gate
canonical_url: https://github.com/sgl-project/sglang/pull/31160
captured_at: '2026-07-14T23:40:21.677969+00:00'
content_hash: 3458caf9a000867a2127b708372bcf6fdcf48f13d84d2889a076b838e3d051a2
---
# Absorb capturer setup and extract the shared-mooncake gate

URL: https://github.com/sgl-project/sglang/pull/31160
State: closed
Labels: 
Closed at: 2026-07-14T08:00:51Z
Merged at: 2026-07-14T08:00:51Z

### mrc-capturer-absorb(absorb-routed-experts-setup-into-routedexpertsca,non_mechanical_provable): Absorb routed-experts setup into RoutedExpertsCapturer.create

Move the enable resolution (enable_return_routed_experts) and num_fused_shared_experts computation from ModelRunner.init_routed_experts_capturer into RoutedExpertsCapturer.create, which now takes the model + model_config and owns its own setup. ModelRunner's method collapses to a single create call.

### mrc-capturer-absorb(absorb-indexer-capturer-setup-into-create-indexe,non_mechanical_provable): Absorb indexer-capturer setup into create_indexer_capturer

Move the enable resolution (enable_return_indexer_topk), the CUDA-only gate, and the num_indexer_layers / index_topk derivation from ModelRunner.init_indexer_capturer into create_indexer_capturer, which now takes model_config and owns its setup (returning None for the disabled / non-CUDA / no-indexer-layer cases). ModelRunner's method collapses to a single create call.

### mrc-capturer-absorb(shared-mooncake-gate-prep,non_mechanical_provable): Extract shared-mooncake gate into a de-self'd maybe_init_shared_mooncake_transfer_engine free function in place

### mrc-capturer-absorb(shared-mooncake-gate-move,mechanical_provable): Move maybe_init_shared_mooncake_transfer_engine to mooncake_transfer_engine (cut+paste)

### mrc-capturer-absorb(shared-mooncake-gate-postpare,non_mechanical_provable): Retarget mooncake test mock to mooncake_transfer_engine.get_local_ip_auto

### mrc-capturer-absorb(split-indexer-capturer,non_mechanical_provable): Split create_indexer_capturer into a setup wrapper and a raw constructor

create_indexer_capturer now only resolves the enable flag, the CUDA-only
gate, and the indexer-layer derivation, then delegates the actual capturer
construction to _create_indexer_capturer_raw, keeping policy and construction
separate.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29316510740](https://github.com/sgl-project/sglang/actions/runs/29316510740)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29316510718](https://github.com/sgl-project/sglang/actions/runs/29316510718)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
