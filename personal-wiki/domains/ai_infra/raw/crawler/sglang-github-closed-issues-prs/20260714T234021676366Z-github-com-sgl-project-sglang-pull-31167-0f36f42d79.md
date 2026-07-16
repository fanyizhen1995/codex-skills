---
source_id: sglang-github-closed-issues-prs
title: Extract attention-backend setup into a module
canonical_url: https://github.com/sgl-project/sglang/pull/31167
captured_at: '2026-07-14T23:40:21.676366+00:00'
content_hash: 0f36f42d79af22293ce4a3f6be8354085599be2b53a93b7123ab7d4afb441176
---
# Extract attention-backend setup into a module

URL: https://github.com/sgl-project/sglang/pull/31167
State: closed
Labels: 
Closed at: 2026-07-14T08:03:49Z
Merged at: 2026-07-14T08:03:49Z

### mrc-attention-backend-setup(extract-attention-backend-setup-prep,non_mechanical_provable): Reshape attention backend setup in place: init_attention_backends orchestrator + de-self'd @staticmethod chain

Consolidate init_aux_hidden_state_capture / init_attention_backend /
_get_attention_backend_from_str into the init_attention_backends orchestrator
plus six model_runner-arg @staticmethods (kept at their class positions), the
AttentionBackends / ResolvedAttentionBackendStr result structs, and thin
wrappers. Stage the destination module header.

### mrc-attention-backend-setup(extract-attention-backend-setup-move,mechanical_provable): move init_attention_backends chain to attention_backend_setup module (cut+paste)







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29316671090](https://github.com/sgl-project/sglang/actions/runs/29316671090)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29316670881](https://github.com/sgl-project/sglang/actions/runs/29316670881)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
