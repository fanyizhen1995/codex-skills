---
source_id: sglang-github-closed-issues-prs
title: '[Bug] [AMD] Accuracy issue with EAGLE speculative decoding and aiter''s unified
  attention for Qwen3.5 FP8 and MXFP4 models'
canonical_url: https://github.com/sgl-project/sglang/issues/24440
captured_at: '2026-07-05T02:14:10.228882+00:00'
content_hash: b323d8b408d68f4e156ceb8c1340711e464fb729e8689ea8ac2d3acb88c99143
---
# [Bug] [AMD] Accuracy issue with EAGLE speculative decoding and aiter's unified attention for Qwen3.5 FP8 and MXFP4 models

URL: https://github.com/sgl-project/sglang/issues/24440
State: closed
Labels: inactive, amd
Closed at: 2026-07-05T00:41:36Z
Merged at: 

### Checklist

- [ ] I searched related issues but found no solution.
- [ ] The bug persists in the latest version.
- [ ] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [ ] Please use English. Otherwise, it will be closed.

### Describe the bug

Accuracy issue when we do not specify `--disable-radix-cache`
Remaining feature from https://github.com/sgl-project/sglang/pull/23146

### Reproduction


```
SGLANG_USE_AITER_UNIFIED_ATTN=1 SGLANG_USE_AITER=1 \
SGLANG_AITER_UNIFIED_VERIFY=1 \
python3 -m sglang.launch_server \
  --model-path /data2/Qwen/Qwen3.5-397B-A17B-FP8 --tp 8 \
  --attention-backend aiter --trust-remote-code \
  --model-loader-extra-config '{"enable_multithread_load": true}' \
  --watchdog-timeout 1200 --mem-fraction-static 0.9 \
  --host 0.0.0.0 --port 9000 \
  --enable-aiter-allreduce-fusion --max-running-requests 128 \
  --page-size 16 \
  --speculative-algorithm EAGLE --speculative-num-steps 3 \
  --speculative-eagle-topk 1 --speculative-num-draft-tokens 4
```

```
SGLANG_USE_AITER_UNIFIED_ATTN=1 SGLANG_USE_AITER=1 \
SGLANG_AITER_UNIFIED_VERIFY=1 \
python3 -m sglang.launch_server \
  --model-path /data/Qwen3.5-397B-A17B-MXFP4 --tp 8 \
  --quantization quark \
  --attention-backend aiter --trust-remote-code \
  --model-loader-extra-config '{"enable_multithread_load": true}' \
  --watchdog-timeout 1200 --mem-fraction-static 0.85 \
  --host 0.0.0.0 --port 9000 --disable-radix-cache \
  --enable-aiter-allreduce-fusion --max-running-requests 128 \
  --page-size 16 \
  --speculative-algorithm EAGLE --speculative-num-steps 3 \
  --speculative-eagle-topk 1 --speculative-num-draft-tokens 4
```

### Environment

On AMD MI355X with `rocm/sgl-dev:v0.5.11-rocm720-mi35x-20260505`

CC: @HaiShaw
