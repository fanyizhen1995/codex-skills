---
source_id: sglang-github-closed-issues-prs
title: '[codex] Test spec-v2 seq-lens CPU opt-out'
canonical_url: https://github.com/sgl-project/sglang/pull/29559
captured_at: '2026-06-29T04:09:41.032167+00:00'
content_hash: c14b0c3bb68ef5ed0b9246cb327e4e6b86121279107cdc76ba4091043414f07b
---
# [codex] Test spec-v2 seq-lens CPU opt-out

URL: https://github.com/sgl-project/sglang/pull/29559
State: closed
Labels: 
Closed at: 2026-06-28T12:36:47Z
Merged at: 

## Summary

Adds regression coverage for the fully-overlapped spec-v2 seq-lens relay contract used by GLM-5.1/DSA:

- verifies `decide_needs_cpu_seq_lens` lets all-GPU metadata backends opt out of the CPU seq-lens mirror
- verifies `FutureMap.resolve_seq_lens_cpu` does not create `seq_lens_cpu`, compute `seq_lens_sum`, or synchronize the D2H stream when `needs_cpu_seq_lens=False`
- statically guards DSA target/draft backend classes so their `needs_cpu_seq_lens = False` opt-out is not accidentally removed

## Trace Notes

The original GLM/MTP trace showed the launch-blocking synchronization in `get_next_batch_to_run -> update_running_batch -> filter_batch -> maybe_wait_verify_done`, with `cudaEventSynchronize` totaling about 96 ms. A fresh main-branch GLM-5.1 dummy DSA/EAGLE trace on `train_31` no longer shows that wait in `get_next_batch_to_run`; remaining SGLang syncs are result-copy waits after the next batch launch path.

## Validation

- `python -m pytest -q test/registered/unit/managers/test_overlap_seq_lens.py` on `train_31`: 4 passed
- GLM-5.1 1-layer dummy DSA/EAGLE TP=1 serving on GPU 0: target verify, draft decode, and draft extend CUDA graphs captured; 2048-token prompt / 100-token generation completed; trace inspected
- GLM-5.1 1-layer dummy DSA/EAGLE TP=2 serving on GPUs 0,1: target verify, draft decode, and draft extend CUDA graphs captured; 512-token prompt / 20-token generation completed
- `test/registered/spec/eagle/test_eagle_constrained_decoding.py` was attempted but blocked by Hugging Face 401 for gated `meta-llama/Llama-2-7b-chat-hf` in this environment







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28319369240](https://github.com/sgl-project/sglang/actions/runs/28319369240)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28319369179](https://github.com/sgl-project/sglang/actions/runs/28319369179)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
