---
source_id: sglang-github-closed-issues-prs
title: '[Spec] Extract shared draft worker construction and generalize draft sampler
  capture'
canonical_url: https://github.com/sgl-project/sglang/pull/30857
captured_at: '2026-07-11T23:37:37.766771+00:00'
content_hash: fdcee45912e6249d9a455ce0fa2c66e981823f182b5e3361901421d0975deb4c
---
# [Spec] Extract shared draft worker construction and generalize draft sampler capture

URL: https://github.com/sgl-project/sglang/pull/30857
State: closed
Labels: deepseek, speculative-decoding, run-ci, run-ci-extra
Closed at: 2026-07-11T19:34:10Z
Merged at: 2026-07-11T19:34:10Z

Behavior-preserving DFLASH refactor, one logical change per commit:

- rename DFlashVerifyInput.num_tokens_per_batch to num_tokens_per_req, matching the field name the attention backends and EagleVerifyInput already use
- require a CUDA device for DFLASH at argument resolution instead of failing mid-startup
- extract draft TpModelWorker construction into draft_worker_common (build_draft_tp_worker, make_draft_input_v2, make_draft_block_spec_info, build_block_pos_offsets); this also dedups two identical draft-input constructions inside the DFLASH worker
- replace the runner's hardcoded dflash_draft_sampler special case with a generic model_runner.capture_tail_hooks list; the DFLASH sampler registers itself as a hook with the same fail-loudly semantics
- extract build_dflash_verify_target_probs from the sampling accept helper

Verification: full test_dflash.py run has an identical pass/fail signature to the main baseline on the same machine (48 passed; the same 3 pre-existing environment-specific failures on both).













































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29162877753](https://github.com/sgl-project/sglang/actions/runs/29162877753)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29162877678](https://github.com/sgl-project/sglang/actions/runs/29162877678)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
