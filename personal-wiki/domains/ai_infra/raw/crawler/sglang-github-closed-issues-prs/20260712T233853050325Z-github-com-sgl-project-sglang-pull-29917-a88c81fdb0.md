---
source_id: sglang-github-closed-issues-prs
title: '[Spec] Add DSpark speculative decoding for Qwen3'
canonical_url: https://github.com/sgl-project/sglang/pull/29917
captured_at: '2026-07-12T23:38:53.050325+00:00'
content_hash: a88c81fdb07c66f78841fd4a8b4b02c7a22f52766607478105bf992ec36b1fda
---
# [Spec] Add DSpark speculative decoding for Qwen3

URL: https://github.com/sgl-project/sglang/pull/29917
State: closed
Labels: speculative-decoding
Closed at: 2026-07-12T22:51:50Z
Merged at: 

## Summary
- Add `Qwen3DSparkDraftModel` (DFlash backbone + Markov/confidence heads) for DeepSpec DSpark Qwen3 checkpoints.
- Extend `DFlashWorkerV2` with Markov block refinement and confidence-aware accept (Triton + eager fallback).
- Route `--speculative-algorithm DSPARK` to DFLASH when draft architecture is `Qwen3DSparkDraftModel`.

## Usage
```bash
sglang serve \
  --model-path <target-qwen3> \
  --speculative-algorithm DSPARK \
  --speculative-draft-model-path <draft-with-Qwen3DSparkDraftModel-config> \
  --speculative-dspark-block-size <block_size>
```

Draft config should set `"architectures": ["Qwen3DSparkDraftModel"]`.

## Test plan
- [ ] `pytest test/registered/unit/spec/test_qwen3_dspark.py`
- [ ] Serve Qwen3-8B + DSpark draft; verify accept len > 1 and stable throughput

Made with [Cursor](https://cursor.com)







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28576537802](https://github.com/sgl-project/sglang/actions/runs/28576537802)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28576537798](https://github.com/sgl-project/sglang/actions/runs/28576537798)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
