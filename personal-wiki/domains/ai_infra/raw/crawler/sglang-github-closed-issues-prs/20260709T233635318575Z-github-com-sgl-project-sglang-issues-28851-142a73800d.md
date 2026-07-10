---
source_id: sglang-github-closed-issues-prs
title: '[Bug] MultiNode Disagg MI355X AMD DeepSeekv4 Pro Accuracy Issues  GSM8k=0.0356'
canonical_url: https://github.com/sgl-project/sglang/issues/28851
captured_at: '2026-07-09T23:36:35.318575+00:00'
content_hash: 142a73800d4580eacbf5f281b3202188e4d8b5478597040cd1c7bb939d4360ff
---
# [Bug] MultiNode Disagg MI355X AMD DeepSeekv4 Pro Accuracy Issues  GSM8k=0.0356

URL: https://github.com/sgl-project/sglang/issues/28851
State: closed
Labels: 
Closed at: 2026-07-09T13:25:22Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

hi @HaiShaw @chunfangamd @billishyahao

Can you take a look at this DeepSeekv4 Pro SGLang accuracy issue on concurrency user 4 on TP8 Prefill + TP8 Decode 

`lmsysorg/sglang-rocm:v0.5.13.post1-rocm720-mi35x-20260615` https://github.com/SemiAnalysisAI/InferenceX/pull/1818

https://github.com/SemiAnalysisAI/InferenceX/actions/runs/27896968169/job/82550287079?pr=1818


## Error Log
```
FAIL: gsm8k exact_match,strict-match = 0.0356 (< 0.91 from models.dsv4)
FAIL: gsm8k exact_match,flexible-extract = 0.0281 (< 0.91 from models.dsv4)
Loaded thresholds from /it-share/gharunners2/gharunner07/actions-runner/_work/InferenceX/InferenceX/utils/evals/thresholds.json
Model prefix: dsv4 (per-model thresholds apply)
PASS: batched eval produced every requested concurrency
PASS: gsm8k exact_match,strict-match = 0.9591 (>= 0.91 from models.dsv4)
PASS: gsm8k exact_match,flexible-extract = 0.9613 (>= 0.91 from models.dsv4)
PASS: gsm8k exact_match,strict-match = 0.9583 (>= 0.91 from models.dsv4)
PASS: gsm8k exact_match,flexible-extract = 0.9598 (>= 0.91 from models.dsv4)
PASS: gsm8k exact_match,strict-match = 0.9568 (>= 0.91 from models.dsv4)
PASS: gsm8k exact_match,flexible-extract = 0.9598 (>= 0.91 from models.dsv4)
PASS: gsm8k exact_match,strict-match = 0.9560 (>= 0.91 from models.dsv4)
PASS: gsm8k exact_match,flexible-extract = 0.9568 (>= 0.91 from models.dsv4)
PASS: gsm8k exact_match,strict-match = 0.9583 (>= 0.91 from models.dsv4)
PASS: gsm8k exact_match,flexible-extract = 0.9598 (>= 0.91 from models.dsv4)
PASS: gsm8k exact_match,strict-match = 0.9598 (>= 0.91 from models.dsv4)
PASS: gsm8k exact_match,flexible-extract = 0.9613 (>= 0.91 from models.dsv4)
PASS: gsm8k exact_match,strict-match = 0.9629 (>= 0.91 from models.dsv4)
PASS: gsm8k exact_match,flexible-extract = 0.9621 (>= 0.91 from models.dsv4)
PASS: gsm8k exact_match,strict-match = 0.9583 (>= 0.91 from models.dsv4)
PASS: gsm8k exact_match,flexible-extract = 0.9606 (>= 0.91 from models.dsv4)
```

## Codex Mapping the Failure to Conc4
<img width="1049" height="727" alt="Image" src="https://github.com/user-attachments/assets/84b6c6f6-eaca-40f9-83a2-e81c4e0724b8" />

### Reproduction

`lmsysorg/sglang-rocm:v0.5.13.post1-rocm720-mi35x-20260615`

### Environment

`lmsysorg/sglang-rocm:v0.5.13.post1-rocm720-mi35x-20260615`
