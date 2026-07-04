---
source_id: sglang-github-closed-issues-prs
title: Fix UE8M0 scale rounding for DeepGEMM
canonical_url: https://github.com/sgl-project/sglang/pull/29956
captured_at: '2026-07-03T02:13:21.695739+00:00'
content_hash: ceef797a2aaf796bda832fdc65b53380d79b5d4a6d04908f903669a1b7221147
---
# Fix UE8M0 scale rounding for DeepGEMM

URL: https://github.com/sgl-project/sglang/pull/29956
State: closed
Labels: run-ci, bypass-fastfail
Closed at: 2026-07-02T20:42:17Z
Merged at: 2026-07-02T20:42:17Z

## Summary

Fix #29954 by making UE8M0 scale rounding bit-exact with DeepGEMM, as suggested in the issue

## Accuracy Test

```bash
sglang serve \
  --model-path zai-org/GLM-5.2-FP8 \
  --tensor-parallel-size 4 \
  --reasoning-parser glm45 \
  --tool-call-parser glm47 \
  --speculative-algorithm EAGLE \
  --speculative-num-steps 5 \
  --speculative-eagle-topk 1 \
  --speculative-num-draft-tokens 6
```

```bash
sgl-eval run gsm8k \
  --base-url http://127.0.0.1:30000/v1 \
  --num-threads 48 \
  --max-tokens 64000 \
  --temperature 1.0 \
  --top-p 0.95

Run directory: /root/.sgl_eval/sgl_eval_gsm8k_20260702-153500
gsm8k: 100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████| 1319/1319 [12:35<00:00,  1.75it/s, acc=97.27%]
== gsm8k ==
1319 examples (single-shot)  |  755.8s  |  1610 tok/s  |  1.2M tokens

* score           =  97.27%
  stop_rate       =  100.00%
  truncated_rate  =  0.00%
  error_rate      =  0.00%

Metrics: /root/.sgl_eval/sgl_eval_gsm8k_20260702-153500/metrics.json
Predictions: /root/.sgl_eval/sgl_eval_gsm8k_20260702-153500  (1 jsonl file(s))
```





























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28606459405](https://github.com/sgl-project/sglang/actions/runs/28606459405)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28606459168](https://github.com/sgl-project/sglang/actions/runs/28606459168)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
