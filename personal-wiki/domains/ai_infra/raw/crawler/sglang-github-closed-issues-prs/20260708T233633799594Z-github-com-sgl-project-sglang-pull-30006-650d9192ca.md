---
source_id: sglang-github-closed-issues-prs
title: Fix prefill CUDA graph disabled for deeply-nested multimodal models
canonical_url: https://github.com/sgl-project/sglang/pull/30006
captured_at: '2026-07-08T23:36:33.799594+00:00'
content_hash: 650d9192ca6f0d359081290ea9ed254679dbf78f746c4176eeaac3765389ba9d
---
# Fix prefill CUDA graph disabled for deeply-nested multimodal models

URL: https://github.com/sgl-project/sglang/pull/30006
State: closed
Labels: intel, run-ci
Closed at: 2026-07-08T04:11:59Z
Merged at: 2026-07-08T04:11:59Z

The prefill CUDA graph layer-resolution only handled two wrapper depths: a direct text model exposing `.layers`, and a CausalLM exposing `.model.layers`. Multimodal models that add another wrapper level -- e.g. DeepSeek-OCR, where the tree is OCR wrapper -> Deepseek*ForCausalLM -> text model -> `.layers` -- fell through to the `else` branch and logged "Disable prefill CUDA graph because the model does not have a 'layers' attribute", silently disabling the prefill graph.

Replace the fixed 2-branch lookup with a descend-until-`layers` loop that walks the `.model` chain to any depth. This keeps the original shallowest- match ordering (so existing models resolve to the same module) while covering the extra-wrapper case.
















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28833427826](https://github.com/sgl-project/sglang/actions/runs/28833427826)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28833427766](https://github.com/sgl-project/sglang/actions/runs/28833427766)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
