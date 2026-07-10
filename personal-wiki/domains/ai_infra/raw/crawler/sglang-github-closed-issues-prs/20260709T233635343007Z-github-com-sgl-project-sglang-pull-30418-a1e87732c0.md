---
source_id: sglang-github-closed-issues-prs
title: 'DO NOT MERGE: revert c016c6f355 to test gb300 glm5-nvfp4 NaN regression'
canonical_url: https://github.com/sgl-project/sglang/pull/30418
captured_at: '2026-07-09T23:36:35.343007+00:00'
content_hash: a1e87732c0a54cc761ce0c9ce81687697db5c09619807eb61f6f1f4a2ab02285
---
# DO NOT MERGE: revert c016c6f355 to test gb300 glm5-nvfp4 NaN regression

URL: https://github.com/sgl-project/sglang/pull/30418
State: closed
Labels: jit-kernel
Closed at: 2026-07-09T00:13:49Z
Merged at: 

## Summary
DO NOT MERGE — debug PR only, used to bisect a nightly failure.

`test/registered/gb300/test_glm52_nvfp4.py` started failing in the nightly-test-perf-4-gpu-gb300 job on 2026-07-07 (run https://github.com/sgl-project/sglang/actions/runs/28833675242), with both `nvidia/GLM-5.2-NVFP4` variants (TP4+MTP, TP4+DP4+DPA+MTP) hitting a CUDA device-side assert:

```
Assertion `NaN detected! sampler: next_token_logits` failed.
Assertion `NaN detected! verify: target model logits` failed.
```

Last known-good nightly run was 2026-07-06 (`8673e85e6c`); first failing run was headSha `6c1fb8a937`. This PR reverts `c016c6f355` ("[JIT Kernel] DeepSeek-V4 DSA indexer: faster top-k + page-table transform (runtime k <= 2048)", #26788), one of the candidate commits in that range touching the DSA indexer math that GLM-5.2-NVFP4 relies on, to see if the NaN goes away.

## Test plan
- [ ] `/rerun-test` to re-run `test/registered/gb300/test_glm52_nvfp4.py` on this branch and confirm whether the NaN assertion disappears











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28888010072](https://github.com/sgl-project/sglang/actions/runs/28888010072)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28888009804](https://github.com/sgl-project/sglang/actions/runs/28888009804)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
