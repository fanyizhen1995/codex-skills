---
source_id: sglang-github-closed-issues-prs
title: Introduce RemoteInstanceWeightTransporter component
canonical_url: https://github.com/sgl-project/sglang/pull/31153
captured_at: '2026-07-14T23:40:21.679776+00:00'
content_hash: 1a38b2f712878af3b55d38e480e4d1f0fb86be9767b50803c87966e554244084
---
# Introduce RemoteInstanceWeightTransporter component

URL: https://github.com/sgl-project/sglang/pull/31153
State: closed
Labels: 
Closed at: 2026-07-14T07:57:43Z
Merged at: 2026-07-14T07:57:43Z

### mrc-remote-instance-weight-transport(rwt-skeleton-prep,non_mechanical_provable): Introduce RemoteInstanceWeightTransport skeleton, rename+de-self init_engine in place, rewire callers and fields

### mrc-remote-instance-weight-transport(rwt-skeleton-move,mechanical_provable): Move init_engine onto RemoteInstanceWeightTransport (cut+paste)

### mrc-remote-instance-weight-transport(rwt-migrate-register-bootstrap-prep,non_mechanical_provable): Prep _register_to_engine_info_bootstrap for move onto RemoteInstanceWeightTransport

### mrc-remote-instance-weight-transport(rwt-migrate-register-bootstrap-move,mechanical_provable): Move _register_to_engine_info_bootstrap onto RemoteInstanceWeightTransport (cut+paste)

### mrc-remote-instance-weight-transport(absorb-remote-instance-weight-info-registration,non_mechanical_provable): Absorb remote-instance weight-info registration into RemoteInstanceWeightTransport

The register_memory_region + _register_to_engine_info_bootstrap gate lived as a
15-line block in ModelRunner.load_model. Move it into
RemoteInstanceWeightTransport.maybe_register_and_publish_weight_info so ModelRunner
keeps a single delegating call; the transport owns its own engine/weight_info
lifecycle.

PR-Title: Introduce RemoteInstanceWeightTransport component

### mrc-remote-instance-weight-transport(rename-transporter,non_mechanical_provable): Rename RemoteInstanceWeightTransport to RemoteInstanceWeightTransporter

Agent-noun naming for the component object; the module file follows:
remote_instance_weight_transport.py -> remote_instance_weight_transporter.py.
The load_model_utils parameter names follow for consistency.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29316318617](https://github.com/sgl-project/sglang/actions/runs/29316318617)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29316318422](https://github.com/sgl-project/sglang/actions/runs/29316318422)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
