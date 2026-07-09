---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Move model-capability adjustments into the resolution pipeline'
canonical_url: https://github.com/sgl-project/sglang/pull/30299
captured_at: '2026-07-08T23:36:33.799125+00:00'
content_hash: b21d14d4df5bf7ac3d5225918376fe72c1596baef788821e48592394d9f0dff9
---
# [refactor] Move model-capability adjustments into the resolution pipeline

URL: https://github.com/sgl-project/sglang/pull/30299
State: closed
Labels: speculative-decoding, ready-to-merge, bypass-fastfail, run-ci-extra
Closed at: 2026-07-08T04:26:56Z
Merged at: 2026-07-08T04:26:56Z

Stacked on #30297; hardens its developer contract ("after `__post_init__`, `server_args` is the resolved configuration") on the write side: configuration is resolved in the pipeline, not by scattered assignments.

- The ModelRunner-era mutations that only depend on the model config move into `__post_init__` as `_handle_model_capability_adjustments`, invoked as the last handler before materialization (mirroring the legacy order, in which the runner-side force ran after the whole pipeline): the HRM-Text prefix-lm force and the multimodal chunked-prefill disable. `refresh_declared_fields` loses its only client and is removed; the scheduler-init dllm page fallback (already folded into the `_dllm_page_size` pass) drops its leftover write.
- The sm<80 float16 fallback stays load-time (it probes the device) but goes through `declare_load_time_override` instead of a bare assignment.
- A **mutation ratchet** (exact pin, like the legacy-getter ratchet) locks the remaining 45 out-of-pipeline assignments, audited into three families — load-/runtime-resolved values, control-plane reconfiguration, per-process deployment wiring — documented in the test. New code must declare through the pipeline instead of assigning `server_args` fields.

🤖 Generated with [Claude Code](https://claude.com/claude-code)













































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28917465068](https://github.com/sgl-project/sglang/actions/runs/28917465068)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28917464993](https://github.com/sgl-project/sglang/actions/runs/28917464993)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
