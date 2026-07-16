---
source_id: sglang-github-closed-issues-prs
title: '[PD] Improve optimistic prefill'
canonical_url: https://github.com/sgl-project/sglang/pull/30951
captured_at: '2026-07-12T23:38:53.051395+00:00'
content_hash: edb66d875995874c3be3b21c162acf7460cb3bf733ac9ab20d7bddb608b0a03e
---
# [PD] Improve optimistic prefill

URL: https://github.com/sgl-project/sglang/pull/30951
State: closed
Labels: run-ci
Closed at: 2026-07-12T22:31:53Z
Merged at: 2026-07-12T22:31:53Z

## Changes
1. Adaptive yield: an optimistic prefill no longer gives up at every chunk boundary but it yields only when a bootstrap-finished request is waiting for the batch.
2. Reframe `retry` to `attempt`: counting total optimistic forward passes instead of requeue. Previously retry limit is 1 means the req has two forward opportunities before bootstrap finished. 
3. Park instead of retry: a request whose prefill finishes before bootstrap completes no longer releases and requeue. It parks in the inflight queue waiting for transfer.

## Fixes along the way.
  - Chunks computed while pending now store their input logprobs.
  - reset_for_retract now clears temp_input_token_ids_logprobs_val/idx.
  - Scheduler prefill log now reports `#optimistic-req` per batch. 









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29210525648](https://github.com/sgl-project/sglang/actions/runs/29210525648)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29210525451](https://github.com/sgl-project/sglang/actions/runs/29210525451)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
