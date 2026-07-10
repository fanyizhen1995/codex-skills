---
source_id: sglang-github-closed-issues-prs
title: Fix garbage output for bare-tekken Mistral checkpoints (e.g. Leanstral)
canonical_url: https://github.com/sgl-project/sglang/pull/30396
captured_at: '2026-07-09T23:36:35.323971+00:00'
content_hash: 4b1c2481cbde31214e48d7a7a2d59fed0a162f8188f132dc48b5b27e4125d63d
---
# Fix garbage output for bare-tekken Mistral checkpoints (e.g. Leanstral)

URL: https://github.com/sgl-project/sglang/pull/30396
State: closed
Labels: run-ci, bypass-fastfail
Closed at: 2026-07-09T18:38:38Z
Merged at: 2026-07-09T18:38:38Z

## Motivation

Serving `mistralai/Leanstral-1.5-119B-A6B` (and any Mistral-native checkpoint that ships only `tekken.json`, no `tokenizer.json`) produces pure garbage output on every hardware / attention backend / TP config, while the same weights work fine on vLLM.

Root cause is in the tokenizer, not the model: `AutoTokenizer` converts `tekken.json` on the fly via transformers' `TekkenConverter`, which assigns BPE ids starting from rank 0 and **drops the 1000 special-token slots that precede the BPE vocab in tekken's id space**. Every encoded id is shifted by 1000:

```
text: "The capital of France is"
mistral-common (reference): [1784, 8961, 1307, 5498, 1395]
converted HF tokenizer:     [784, 112623, 1935, 37166, 275]
```

Ids < 1000 land on untrained special-token embedding rows (all zeros), the rest on wrong rows — garbage in, garbage out. (Even with the offset fixed, the converted tokenizer still splits text differently from mistral-common, so the conversion path is not salvageable.)

## Modifications

- `mistral_utils.py`: add `is_bare_tekken_checkpoint()` — true iff the checkpoint has `tekken.json` but no `tokenizer.json` (local dir or HF cache, no network).
- `tokenizer.py`: route such checkpoints to `transformers.tokenization_mistral_common.MistralCommonTokenizer` (mistral-common backed; `mistral_common` is already a hard dependency). The result still goes through `_apply_post_load_fixes`, same as the existing Voxtral/Pixtral MistralCommon path. Checkpoints that ship an official `tokenizer.json` are unaffected.
- Unit test: detection logic + end-to-end encode parity against the mistral-common reference ids using the real Leanstral `tekken.json`.

## Verification

On 4×H200 (TP4, fa3) serving Leanstral-1.5-119B-A6B from the Mistral-native checkpoint:

- Before: `"The capital of France is"` → `" ÐµÑĢ äº ada ew ption ..."`; after: `" Paris. Paris is the largest city in France..."`
- GSM8K (sgl-eval, full 1319, temp 1.0 / top_p 0.95): **accuracy 91.13%, stop rate 99.92%**, 0 errors — matches vLLM behavior on the same weights.
- `pytest test/registered/unit/tokenizer/test_tekken_tokenizer_routing.py` → 2 passed.











































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28984842888](https://github.com/sgl-project/sglang/actions/runs/28984842888)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28984842738](https://github.com/sgl-project/sglang/actions/runs/28984842738)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
