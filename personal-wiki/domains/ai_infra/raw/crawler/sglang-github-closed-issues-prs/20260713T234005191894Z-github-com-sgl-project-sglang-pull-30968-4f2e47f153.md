---
source_id: sglang-github-closed-issues-prs
title: '[Bugfix] Fix Nemotron ForwardFlags across custom op boundary'
canonical_url: https://github.com/sgl-project/sglang/pull/30968
captured_at: '2026-07-13T23:40:05.191894+00:00'
content_hash: 4f2e47f153b325f5e4a9b198012a6d379aae0e1047b1996fc4740360c31449a2
---
# [Bugfix] Fix Nemotron ForwardFlags across custom op boundary

URL: https://github.com/sgl-project/sglang/pull/30968
State: closed
Labels: high priority, run-ci, bypass-fastfail, run-ci-extra
Closed at: 2026-07-13T05:10:23Z
Merged at: 2026-07-13T05:10:23Z

## Summary

#30802 moved the Nemotron all-reduce fusion flag into `ForwardFlags`. That works for normal calls, but the Mamba custom op can run after the flag's scope is gone. It then reads the wrong value, runs an extra all-reduce, and hurts accuracy.

CI did not catch this because a FlashInfer workspace error silently disabled fusion. #30580 fixed that error and exposed the bug. The fix is small. We pass the flag into the custom op and set it again inside.

## Accuracy

```bash
CI=true PYTHONUNBUFFERED=1 python registered/models_e2e/test_nvidia_nemotron_3_nano.py -v

gsm8k | exact_match,strict-match: ground_truth=0.847 | measured=0.845 | rtol=0.08
[METRIC] gsm8k_exact_match,strict-match=0.8453373768006065 labels={"model": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8", "eval": "lm-eval", "task": "gsm8k"}
gsm8k | exact_match,flexible-extract: ground_truth=0.556 | measured=0.558 | rtol=0.08
[METRIC] gsm8k_exact_match,flexible-extract=0.5579984836997726 labels={"model": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8", "eval": "lm-eval", "task": "gsm8k"}
```



































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29222775887](https://github.com/sgl-project/sglang/actions/runs/29222775887)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29222775748](https://github.com/sgl-project/sglang/actions/runs/29222775748)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
