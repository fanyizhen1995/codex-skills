---
source_id: sglang-github-closed-issues-prs
title: skip TP narrow when w2 scales already match shard size (#22421)
canonical_url: https://github.com/sgl-project/sglang/pull/22476
captured_at: '2026-07-13T23:40:05.177198+00:00'
content_hash: 48d7da8a736d9c7ba6d494c0b17721baf346c307e54a54f798793c5a56c16f50
---
# skip TP narrow when w2 scales already match shard size (#22421)

URL: https://github.com/sgl-project/sglang/pull/22476
State: closed
Labels: 
Closed at: 2026-07-13T18:39:33Z
Merged at: 

## Summary
Guard the `narrow()` call in `_load_w2()` to skip TP slicing when the loaded weight already matches the parameter shard size. Fixes `IndexError: start out of range` when loading GPTQ-Int4 MoE models with `desc_act=False` and `tp_size > 1`.

Closes #22421.
