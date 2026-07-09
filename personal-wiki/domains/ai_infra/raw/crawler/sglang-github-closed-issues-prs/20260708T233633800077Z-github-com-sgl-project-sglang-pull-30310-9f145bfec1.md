---
source_id: sglang-github-closed-issues-prs
title: Increase the KV cache pool when using indexShare by 15%
canonical_url: https://github.com/sgl-project/sglang/pull/30310
captured_at: '2026-07-08T23:36:33.800077+00:00'
content_hash: 9f145bfec1974f96c7edcbb8a19585537ff3575c2ded1eba939ceb89188a138b
---
# Increase the KV cache pool when using indexShare by 15%

URL: https://github.com/sgl-project/sglang/pull/30310
State: closed
Labels: run-ci
Closed at: 2026-07-08T03:59:14Z
Merged at: 2026-07-08T03:59:14Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

This issue is discovered by @vincentzed. On skip topk and indexer layers, we'd better not allocate the memory here

The KV cache pool go from 2,430,528 to 2,813,952 tokens (15%) increase, it save 18 GB per rank.

NOTE: we'd actually need to skip indexer init completely and gain 1 more GB per rank. But this is a quick fix to recover 95% of the waste

```
sglang serve \
    --trust-remote-code \
    --model-path nvidia/GLM-5.2-NVFP4 \
    --tp 4 \
    --quantization modelopt_fp4 \
    --speculative-algorithm EAGLE \
    --speculative-num-steps 5 \
    --speculative-eagle-topk 1 \
    --speculative-num-draft-tokens 6
```

<!-- Describe the purpose and goals of this pull request. -->

<!-- Detail the changes made in this pull request. -->

## Accuracy Tests

```
sgl-eval run aime25 \
    --base-url http://localhost:30000/v1 \
    --n-repeats 8 \
    --max-tokens 65536 \
    --temperature 1.0 \
    --top-p 0.95 \
    --num-threads 128
Run directory: /root/.sgl_eval/sgl_eval_aime25_20260707-001907
aime25 rep 1/8: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 30/30 [18:52<00:00, 37.74s/it, acc=93.33%]
aime25 rep 2/8: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 30/30 [18:52<00:00, 37.74s/it, acc=93.33%]
aime25 rep 3/8: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 30/30 [18:52<00:00, 37.74s/it, acc=86.67%]
aime25 rep 4/8: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 30/30 [18:52<00:00, 37.74s/it, acc=90.00%]
aime25 rep 5/8: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 30/30 [18:52<00:00, 37.74s/it, acc=93.33%]
aime25 rep 6/8: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 30/30 [18:52<00:00, 37.74s/it, acc=93.33%]
aime25 rep 7/8: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 30/30 [18:52<00:00, 37.74s/it, acc=93.33%]
aime25 rep 8/8: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 30/30 [18:52<00:00, 37.74s/it, acc=86.67%]
aime25 overall: 100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 240/240 [18:52<00:00,  4.72s/it, acc=91.25%]
== aime25 ==
30 examples x 8 repeats  |  1132.1s  |  4252 tok/s  |  4.8M tokens

* pass@1[avg-of-8]  =  91.25% +/- 3.05% (SEM 1.08%)
  pass@8            =  96.67%
  majority@8        =  93.33%
  no_answer         =  0.00%
  stop_rate         =  100.00%
  truncated_rate    =  0.00%
  error_rate        =  0.00%

Metrics: /root/.sgl_eval/sgl_eval_aime25_20260707-001907/metrics.json
Predictions: /root/.sgl_eval/sgl_eval_aime25_20260707-001907  (8 jsonl file(s))
```

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28906467414](https://github.com/sgl-project/sglang/actions/runs/28906467414)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28906467339](https://github.com/sgl-project/sglang/actions/runs/28906467339)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
