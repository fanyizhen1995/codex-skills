---
source_id: sglang-github-closed-issues-prs
title: '[Fix] Unify ForwardBatch extend lens cpu fields to their declared list type'
canonical_url: https://github.com/sgl-project/sglang/pull/30896
captured_at: '2026-07-11T23:37:37.766503+00:00'
content_hash: 0e418c032ee0d31680ca4e1d317432e676836ecd26da800ac1bba527cb565a85
---
# [Fix] Unify ForwardBatch extend lens cpu fields to their declared list type

URL: https://github.com/sgl-project/sglang/pull/30896
State: closed
Labels: blackwell, run-ci
Closed at: 2026-07-11T22:30:53Z
Merged at: 2026-07-11T22:30:53Z

The three extend lens cpu fields are declared `Optional[List[int]]`, and the `*_cpu` family convention is: tensor mirrors (`seq_lens_cpu`) stay tensors, host bookkeeping lists (`encoder_lens_cpu`, `global_num_tokens_cpu`, `extend_*_cpu`) stay lists. Two producers violated this and stored CPU tensors instead (the mlp-sync decode-as-extend adjustment and the prefill cuda-graph capture batch), so downstream `sum()`/`max()` silently produce 0-dim tensors instead of ints — `trtllm_mha_backend` and `kda_flashkda` already carry defensive workarounds for exactly this.

This normalizes both producers to lists and drops the now-dead workaround in `trtllm_mha_backend`. Test-side producers that constructed these fields as CPU tensors (`test_flashattn_backend`, `test_flashattn_mla_backend`, `test_dsa_indexer`) are normalized to lists as well.

























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29170511830](https://github.com/sgl-project/sglang/actions/runs/29170511830)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29170511748](https://github.com/sgl-project/sglang/actions/runs/29170511748)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
