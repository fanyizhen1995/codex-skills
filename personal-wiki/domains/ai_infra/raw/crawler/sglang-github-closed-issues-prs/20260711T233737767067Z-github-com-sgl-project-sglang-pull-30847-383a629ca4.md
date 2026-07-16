---
source_id: sglang-github-closed-issues-prs
title: '[Fix] Guard kernel OOB accesses and harden runtime edge cases'
canonical_url: https://github.com/sgl-project/sglang/pull/30847
captured_at: '2026-07-11T23:37:37.767067+00:00'
content_hash: 383a629ca4f6001b49ae02b0dbb0e14eb1ed7f7ab2d42a19f5439efa256d81ca
---
# [Fix] Guard kernel OOB accesses and harden runtime edge cases

URL: https://github.com/sgl-project/sglang/pull/30847
State: closed
Labels: run-ci, jit-kernel
Closed at: 2026-07-11T19:22:13Z
Merged at: 2026-07-11T19:22:13Z

Small independent fixes, one commit each:

- eplb: fall back to identity mapping when a layer id exceeds the physical expert map (draft workers can query more MoE layers than the target-sized map covers)
- deepseek_v4 norm-rope kernel: skip rows with a negative out_loc sentinel instead of writing out of bounds
- trtllm_mha page-table kernel: clamp the SWA gather index into full_to_swa bounds
- forward_batch_info: guard lora_ids extend when None; skip next_token_logits truncation when a forward returns hidden states only
- ParallelLMHead: forward enable_tp to VocabParallelEmbedding
- one_batch_server: read spec metrics from all internal states (multi-DP servers report them on non-zero ranks)
- hf config registry: register the gemma4_unified alias so AutoConfig resolves the existing model type
- model_runner: draft workers with multi-stage models read num_stages for the layer count











































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29145944765](https://github.com/sgl-project/sglang/actions/runs/29145944765)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29145944682](https://github.com/sgl-project/sglang/actions/runs/29145944682)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
