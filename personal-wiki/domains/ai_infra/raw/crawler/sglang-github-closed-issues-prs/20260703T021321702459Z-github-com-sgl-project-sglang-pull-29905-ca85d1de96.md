---
source_id: sglang-github-closed-issues-prs
title: 'docs: add Qwen3.6-27B-NVFP4 variant to cookbook'
canonical_url: https://github.com/sgl-project/sglang/pull/29905
captured_at: '2026-07-03T02:13:21.702459+00:00'
content_hash: ca85d1de96dc022bb82d882206d683171fae6dea431814deca3fbb94e13a95c4
---
# docs: add Qwen3.6-27B-NVFP4 variant to cookbook

URL: https://github.com/sgl-project/sglang/pull/29905
State: closed
Labels: documentation
Closed at: 2026-07-02T07:05:30Z
Merged at: 2026-07-02T07:05:30Z

## Motivation

Add the `nvidia/Qwen3.6-27B-NVFP4` (Blackwell) checkpoint to the Qwen3.6 cookbook page so users can generate deployment commands for the NVFP4 variant.

## Modifications

- **Command generator** (`qwen36-deployment.jsx`): expose an **NVFP4** quantization option, surfaced only for **27B + B200/B300** (NVFP4 is a Blackwell-only, 27B-only checkpoint). It emits the checkpoint's documented command shape — explicit `--tp-size 1`, `--attention-backend trtllm_mha`, new-style `--mamba-radix-cache-strategy`, and explicit `--host`/`--port`. The reasoning and tool-call parsers still follow their existing toggles.
- **Available Models** table: add a `Qwen3.6-27B (NVFP4)` row linking to the HF repo.
- **Installation** section: add the dedicated dev image `lmsysorg/sglang:dev-cu13-dev-qwen36-27b-nvfp4`.

Generated command (B200/B300, MTP on, parsers on):

```
sglang serve --model-path nvidia/Qwen3.6-27B-NVFP4 \
  --tp-size 1 --attention-backend trtllm_mha \
  --reasoning-parser qwen3 \
  --tool-call-parser qwen3_coder \
  --speculative-algorithm EAGLE --speculative-num-steps 3 \
  --speculative-eagle-topk 1 --speculative-num-draft-tokens 4 \
  --mamba-radix-cache-strategy extra_buffer \
  --host 0.0.0.0 --port 30000
```

## Checklist

- [x] `mint validate` passes (build validation)
- [x] Docs-only change (Mintlify cookbook)

🤖 Generated with [Claude Code](https://claude.com/claude-code)









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28571649289](https://github.com/sgl-project/sglang/actions/runs/28571649289)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28571649172](https://github.com/sgl-project/sglang/actions/runs/28571649172)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
