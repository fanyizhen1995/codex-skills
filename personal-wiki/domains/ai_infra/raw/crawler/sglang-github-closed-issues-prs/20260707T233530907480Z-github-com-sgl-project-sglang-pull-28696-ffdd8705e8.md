---
source_id: sglang-github-closed-issues-prs
title: '[DO NOT MERGE] CI timeout bump to validate 8-gpu nightly tests (#27705)'
canonical_url: https://github.com/sgl-project/sglang/pull/28696
captured_at: '2026-07-07T23:35:30.907480+00:00'
content_hash: ffdd8705e8be107b8b40a1aee778723495e227cd18a17a0ea3a405aac86094a8
---
# [DO NOT MERGE] CI timeout bump to validate 8-gpu nightly tests (#27705)

URL: https://github.com/sgl-project/sglang/pull/28696
State: closed
Labels: lora, deepseek, jit-kernel
Closed at: 2026-07-07T18:05:22Z
Merged at: 

Throwaway branch off #27705 (`brayden/remove-hadamard`) with **only** a two-line bump to `rerun-test.yml` cuda-job timeouts (job 120→240, step 60→200).

Purpose: validate `test_glm_51_fp8.py` and `test_deepseek_v32.py` via `/rerun-test` without hitting the 60-min step cap. Test code is identical to #27705, so green here = valid signal for #27705.

**Do not merge. Delete after validation.**











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #27799233442](https://github.com/sgl-project/sglang/actions/runs/27799233442)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27799233278](https://github.com/sgl-project/sglang/actions/runs/27799233278)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
