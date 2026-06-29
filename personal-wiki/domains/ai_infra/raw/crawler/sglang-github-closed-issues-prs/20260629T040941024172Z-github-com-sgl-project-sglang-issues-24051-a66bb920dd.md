---
source_id: sglang-github-closed-issues-prs
title: '[Bug] STANDALONE speculative decoding silently corrupts output when draft/target
  vocabularies differ'
canonical_url: https://github.com/sgl-project/sglang/issues/24051
captured_at: '2026-06-29T04:09:41.024172+00:00'
content_hash: a66bb920ddbcdea095b920736b29d5d2d5e60f6e36262d7240cfd15cef7f6cdf
---
# [Bug] STANDALONE speculative decoding silently corrupts output when draft/target vocabularies differ

URL: https://github.com/sgl-project/sglang/issues/24051
State: closed
Labels: inactive
Closed at: 2026-06-29T00:51:17Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

`STANDALONE` speculative decoding requires the draft model to share the same vocabulary as the target model. If the vocabularies differ, draft token IDs map to different strings in the target vocabulary — the server starts without any error or warning and every accepted draft token is silently corrupted.

**Root cause:** the STANDALONE token-ID data flow is: (1) draft forward pass → token IDs, (2) target verifies those IDs, (3) target decodes accepted IDs using its own vocabulary. If the two tokenizers map the same integer to different strings, step 3 produces garbage for every accepted token. SGLang currently performs no validation of vocabulary compatibility at startup.

**What should happen:** SGLang should raise a `ValueError` at startup (before serving any request) when the draft and target vocabularies are incompatible, and suggest `--speculative-algorithm TLI` ([PR #22883](https://github.com/sgl-project/sglang/pull/22883)) for cross-family pairs.

**Notes:**
- This affects only `STANDALONE` mode; `EAGLE` and `TLI` ([PR #22883](https://github.com/sgl-project/sglang/pull/22883)) are not impacted.
- The subtler case — same `vocab_size` but different token-to-ID mappings — should also be caught.
- Prior art: HuggingFace Transformers uses the same `get_vocab()` dict comparison to distinguish homogeneous from heterogeneous vocabulary pairs ([transformers PR #35029](https://github.com/huggingface/transformers/pull/35029)).
- A fix is proposed in [PR #23838](https://github.com/sgl-project/sglang/pull/23838).

### Reproduction

Launch a server with mismatched draft/target models, e.g. `google/gemma-2-9b` (vocab 256,000) as target and `bigcode/tiny_starcoder_py` (vocab 49,152) as draft:

```bash
python -m sglang.launch_server \
    --model-path google/gemma-2-9b \
    --speculative-algorithm STANDALONE \
    --speculative-draft-model-path bigcode/tiny_starcoder_py \
    --speculative-num-steps 5 \
    --speculative-eagle-topk 1 \
    --speculative-num-draft-tokens 5
```

The server starts without any error or warning. Every accepted draft token is silently corrupted.

Two minimal demo scripts are available as a [public gist](https://gist.github.com/jmamou/34e0c08153e662054c92f4c40d0158bd):

**`demo_vocab_mismatch_bug.py`** — CPU-only, tokenizer files only. Shows that the same token ID decodes to different strings in each vocabulary and simulates the STANDALONE data flow:

```bash
pip install tokenizers
python demo_vocab_mismatch_bug.py --mode buggy
```

Sample output:
```
prompt         : 'def add(a, b): return a + b'
draft IDs      : [589, 1015, 26, 83, 30, 323, 711, 442, 312, 474, 323]
target decodes : ' = imp<unused19><unused76><unused23>jure…'  <<< SILENT CORRUPTION

prompt         : 'The capital of France is'
draft IDs      : [1318, 18926, 432, 45600, 438]
target decodes : 'те वि… Pix…'  <<< SILENT CORRUPTION
```

**`demo_real_inference.py`** — runs actual model forward passes (`openai-community/gpt2` as target, `bigcode/tiny_starcoder_py` as draft, ~200 MB each). All 12 generated tokens are corrupted on every prompt:

```bash
pip install transformers torch
python demo_real_inference.py
```

Sample output:
```
Prompt          : 'The capital of France is'
Target-only     : ' the capital of the French Republic, and the capital of the'  ✓ correct
Buggy STANDALONE: '▯DLLCACCCACC'  ✗ CORRUPTED

Prompt          : 'def add(a, b):'
Target-only     : '\n\nreturn a + b\n\ndef add(a'  ✓ correct
Buggy STANDALONE: ' to chid jayect\x0fasereen;t?'  ✗ CORRUPTED
```

### Environment


```
Python: 3.10.19 | packaged by conda-forge | (main, Oct 22 2025, 22:29:10) [GCC 14.3.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA RTX A6000
GPU 0,1,2,3,4,5,6,7 Compute Capability: 8.6
CUDA_HOME: /usr/local/cuda-13
NVCC: Cuda compilation tools, release 13.0, V13.0.48
CUDA Driver Version: 580.65.06
PyTorch: 2.8.0+cu126
sglang: 0.0.0.dev11628+g074c2a476.d20260415
flashinfer_python: 0.6.7.post3
triton: 3.4.0
transformers: 4.57.1
```
