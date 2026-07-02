---
source_id: sglang-github-closed-issues-prs
title: '[Feature] Support weightless RMSNorm (for FlashNorm weight folding trick)'
canonical_url: https://github.com/sgl-project/sglang/issues/24206
captured_at: '2026-07-01T02:12:08.948821+00:00'
content_hash: 717aee1d312a0595eb4af830bf4510d743fb148851ec40d04fedc04b5f01847f
---
# [Feature] Support weightless RMSNorm (for FlashNorm weight folding trick)

URL: https://github.com/sgl-project/sglang/issues/24206
State: closed
Labels: inactive
Closed at: 2026-07-01T00:51:30Z
Merged at: 

### Checklist

- [x] If this is not a feature request but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Motivation

Please add support for RMSNorm without normalization weights.

This is to support [FlashNorm](https://arxiv.org/abs/2407.09577) — a mathematically equivalent variant of RMSNorm that folds norm weights into the subsequent linear layer.  [See explainer video](https://www.youtube.com/watch?v=GEuJv34_XgU).

We have applied this weight folding trick to a few LLMs (Llama, Qwen, SMolLM) here:
https://huggingface.co/models?other=weightless-rmsnorm 


<img width="332" height="183" alt="Image" src="https://github.com/user-attachments/assets/d97b50ba-1092-4d44-ad70-ff2bca448b1d" />

### Motivation

FlashNorm's removal of norm weights reduces inference overhead at zero accuracy cost, and we'd like to share these optimized models with the broader community.

### Possible Implementation

Remove norm weights from your RMSNorm implementation. E.g., just skip norm weight multiplication if there are no norm weights provided.


### Related resources

[FlashNorm paper](https://arxiv.org/abs/2407.09577)
[explainer video](https://www.youtube.com/watch?v=GEuJv34_XgU)
