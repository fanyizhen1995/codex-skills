---
source_id: sglang-github-closed-issues-prs
title: '[Bug] cached_tokens Reports 0 with MTP/Speculative Decoding, Breaking Cache
  Hit Rate Metrics'
canonical_url: https://github.com/sgl-project/sglang/issues/20451
captured_at: '2026-07-05T02:14:10.230255+00:00'
content_hash: 4ee98b5c297193715ff17aff772327d0e8d5de6bed2601a152b043e07d9f199f
---
# [Bug] cached_tokens Reports 0 with MTP/Speculative Decoding, Breaking Cache Hit Rate Metrics

URL: https://github.com/sgl-project/sglang/issues/20451
State: closed
Labels: inactive
Closed at: 2026-07-05T00:41:34Z
Merged at: 

### Checklist

- [ ] I searched related issues but found no solution.
- [ ] The bug persists in the latest version.
- [ ] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [ ] Please use English. Otherwise, it will be closed.

### Describe the bug

When MTP (Multi-Token Prediction / Speculative Decoding) is enabled, cached_tokens always reports 0 even when prefix caching (RadixCache or HiCache) is enabled. This causes Cache Hit Rate to be incorrectly reported as 0%.

### Reproduction

### 1. Start server with MTP enabled
```bash
python -m sglang.launch_server \
    --model-path Qwen/Qwen3-32B \
    --port 30000 \
    --tp-size 4 \
    --speculative-num-steps 5 \
    --speculative-eagle-topk 8 \
    --speculative-num-draft-tokens 64
```

### 2. Run multi-turn benchmark
```bash
python benchmark/hicache/bench_multiturn.py \
    --model-path Qwen/Qwen3-32B \
    --dataset-path ShareGPT_V3_unfiltered_cleaned_split.json \
    --port 30000 \
    --request-length 512 \
    --num-clients 64 \
    --num-rounds 5 \
    --max-parallel 32
```

### 3. Observe results
```
Cache Hit Rate: 0.000000  # Expected: > 0
```

### Control test (MTP disabled)
```bash
python -m sglang.launch_server \
    --model-path Qwen/Qwen3-32B \
    --port 30000 \
    --tp-size 4
    # No speculative decoding flags

# Run same benchmark
python benchmark/hicache/bench_multiturn.py ...

# Result: Cache Hit Rate: 0.650000 (correct)
```

### Environment

sglang==0.5.9
