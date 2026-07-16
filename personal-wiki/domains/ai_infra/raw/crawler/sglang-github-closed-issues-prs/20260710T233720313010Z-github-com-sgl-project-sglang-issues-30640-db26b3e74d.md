---
source_id: sglang-github-closed-issues-prs
title: '[Bug] TiktokenTokenizer missing num_special_tokens_to_add breaks bench_serving
  random dataset (Grok-2)'
canonical_url: https://github.com/sgl-project/sglang/issues/30640
captured_at: '2026-07-10T23:37:20.313010+00:00'
content_hash: db26b3e74d680e68adb32f408d774ae922df942ca9accde04a3abb850f06d793
---
# [Bug] TiktokenTokenizer missing num_special_tokens_to_add breaks bench_serving random dataset (Grok-2)

URL: https://github.com/sgl-project/sglang/issues/30640
State: closed
Labels: 
Closed at: 2026-07-10T12:37:33Z
Merged at: 

### Checklist

- [x] Searched existing issues (no match for `num_special_tokens_to_add` / TiktokenTokenizer)
- [x] Reproduced on latest ROCm image `lmsysorg/sglang-rocm:v0.5.14-rocm720-mi35x-20260708`

### Describe the bug

`sglang.srt.tokenizer.tiktoken_tokenizer.TiktokenTokenizer` (used for xAI **Grok-2**, whose HF repo `xai-org/grok-2` ships only `tokenizer.tok.json` and no `tokenizer.json`) does not implement `num_special_tokens_to_add()`.

`sglang.bench_serving` with the default `--dataset-name random` (text mode) calls it at `python/sglang/benchmark/datasets/random.py:80`:

```python
if return_text:
    num_special_tokens = int(tokenizer.num_special_tokens_to_add())
```

so benchmarking Grok-2 crashes with:

```
AttributeError: 'TiktokenTokenizer' object has no attribute 'num_special_tokens_to_add'
```

This is a sibling gap to #29853 (which fixed `all_special_ids` in `patch_tokenizer.decode_without_hf_kwargs`). `TiktokenTokenizer` is still missing `num_special_tokens_to_add` (and `all_special_ids`).

### Minimal reproduction (CPU only, no GPU / no weights)

```python
from sglang.srt.tokenizer.tiktoken_tokenizer import TiktokenTokenizer
t = TiktokenTokenizer("<path>/tokenizer.tok.json")  # e.g. from xai-org/grok-2
print(type(t).__name__)                       # TiktokenTokenizer
print(hasattr(t, "num_special_tokens_to_add"))# False
print(hasattr(t, "all_special_ids"))          # False
t.num_special_tokens_to_add()                 # AttributeError
# encode/decode themselves work fine:
ids = t.encode("hello world")                 # [21517, 1749]
print(t.decode(ids))                          # 'hello world'
```

End-to-end (what actually fails):

```bash
python -m sglang.launch_server --model-path xai-org/grok-2 \
  --tokenizer-path <snapshot>/tokenizer.tok.json \
  --dtype bfloat16 --quantization fp8 --tp-size 8 --trust-remote-code
python -m sglang.bench_serving --backend sglang --base-url http://localhost:8000 \
  --model xai-org/grok-2 --dataset-name random \
  --random-input-len 1024 --random-output-len 1024 --max-concurrency 8 --num-prompts 80
# -> AttributeError at benchmark/datasets/random.py:80
```

### Expected behavior

`bench_serving --dataset-name random` should work with tekken tokenizers, as it does for standard HF tokenizers. tekken `encode` adds no special tokens (`encode(x, add_special_tokens=False) -> self.tokenizer.encode(x)`), so `num_special_tokens_to_add()` should return `0`.

### Proposed fix

Add to `TiktokenTokenizer` (`python/sglang/srt/tokenizer/tiktoken_tokenizer.py`):

```python
def num_special_tokens_to_add(self, *args, **kwargs) -> int:
    return 0
```

(Optionally also expose `all_special_ids = []` for symmetry with the #29853 detokenizer path.)

### Workaround

Passing `--tokenize-prompt` to `bench_serving` avoids the call (it is gated behind `if return_text:`, and `return_text = not args.tokenize_prompt`).

### Environment

- Image: `lmsysorg/sglang-rocm:v0.5.14-rocm720-mi35x-20260708` (SGLang 0.5.14.dev, ROCm 7.2)
- Hardware: 8x AMD Instinct MI350X (gfx950)
- Model: `xai-org/grok-2` (BF16, tekken `tokenizer.tok.json`, online `--quantization fp8`), TP=8
