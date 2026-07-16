---
source_id: sglang-github-closed-issues-prs
title: '[Bug] FlashInfer MIS appears to use full-sequence delimiter indices after
  radix-cache prefix hits'
canonical_url: https://github.com/sgl-project/sglang/issues/26618
captured_at: '2026-07-10T23:37:20.316154+00:00'
content_hash: ad5bbb7ae5339d12afa6eb214b0b3cf1c551dae5047180c1e190884e603f99bf
---
# [Bug] FlashInfer MIS appears to use full-sequence delimiter indices after radix-cache prefix hits

URL: https://github.com/sgl-project/sglang/issues/26618
State: closed
Labels: 
Closed at: 2026-07-10T01:24:13Z
Merged at: 

### What I tested

I investigated Multi-Item Scoring (MIS) with FlashInfer attention and radix/prefix cache behavior on current `main`.

Important caveat: current `main` intentionally masks this through `ServerArgs._handle_multi_item_scoring()`:

```python
if not self.disable_radix_cache:
    logger.warning("Radix cache is disabled because --enable-mis is set.")
    self.disable_radix_cache = True
```

So the public config `enable_mis=True, disable_radix_cache=False` does not actually exercise radix hits today. I first verified that path: SGLang logged `Radix cache is disabled because --enable-mis is set`, all MIS debug records had `extend_prefix_lens_cpu=[0]`, and radix/no-radix scores matched.

To validate the underlying FlashInfer MIS path, I then used a temporary local guard bypass only for this repro, so MIS could run with real prefix-cache hits:

```python
force_mis_radix_cache = os.environ.get("SGLANG_MIS_FORCE_RADIX_CACHE") == "1"
if not self.disable_radix_cache and not force_mis_radix_cache:
    ...
```

I also added temporary logging/asserts in `FlashInferAttnBackend._process_multi_item_scoring` for:

`extend_seq_lens_cpu`, `extend_prefix_lens_cpu`, `delimiter_indices`, `first_delim`, `suffix_len`, `seq_start/seq_end`, `len(prefix_len_ptr)`, and `token_pos_in_items_len`.

### Environment

- Commit: `ec78fa65184e0f5ecc2976b71bdbaeac922e3e08`
- SGLang: `0.5.12.post2.dev562+gec78fa651`
- GPU: `NVIDIA A100-SXM4-40GB`
- Torch: `2.11.0+cu130`
- CUDA runtime reported by torch: `13.0`
- Driver: `580.159.03`
- FlashInfer: `flashinfer-python 0.6.11.post1`, `flashinfer-cubin 0.6.11.post1`

### Repro shape

Score-only repro, no mixed score+generate batching:

```python
Engine(
    model_path="tomaarsen/Qwen3-Reranker-0.6B-seq-cls",
    enable_mis=True,
    attention_backend="flashinfer",
    chunked_prefill_size=-1,
    disable_radix_cache=False,
    mem_fraction_static=0.25,
)
```

Then:

1. Score a long shared-prefix multi-item request once to warm radix cache.
2. Repeat the same score request.

The long request was sequence-classification MIS so prefix matching was not clamped by the generation score path's `logprob_start_len=0`.

### Actual behavior with radix cache forced on

The warm request has no prefix hit and is fine:

```text
MIS_DEBUG req=0 extend_seq_lens_cpu=[473] extend_prefix_lens_cpu=[0] delimiter_indices=[446, 452, 458, 465, 472] first_delim=446 suffix_len=27 seq_start=0 seq_end=473 len(prefix_len_ptr)=1 token_pos_in_items_len=0
```

The repeated request hits radix cache and then `_process_multi_item_scoring` uses the full-sequence delimiter index against the extend-only slice:

```text
MIS_DEBUG req=0 extend_seq_lens_cpu=[1] extend_prefix_lens_cpu=[472] delimiter_indices=[446, 452, 458, 465, 472] first_delim=446 suffix_len=-445 seq_start=0 seq_end=1 len(prefix_len_ptr)=1 token_pos_in_items_len=0
```

That tripped the temporary assertion:

```text
AssertionError: MIS delimiter index is outside the current FlashInfer extend slice: req=0, first_delim=446, extend_seq_len=1, prefix_cache_len=472, delimiter_indices=[446, 452, 458, 465, 472]
```

This appears consistent with full-sequence delimiter indices not being adjusted for `extend_prefix_lens_cpu` / the current extend offset before they are used by FlashInfer MIS metadata construction.

### Expected behavior

If radix cache is supported for MIS in the future, delimiter positions should be rebased to the current extend slice, or the FlashInfer MIS metadata path should otherwise account for cached prefix length. Alternatively, keeping MIS radix disabled is appropriate, but the underlying reason appears to be this delimiter/extend-slice mismatch.

### Duplicate check

I searched open and closed issues/PRs for:

- `enable_mis radix cache`
- `multi_item_delimiter_indices radix`
- `Multi-Item Scoring radix`
- `prefix_len_ptr delimiter`
- the exact assertion/log text above

I did not find this issue. I saw #25414, but that is the known mixed score+generate batching bug and this repro is score-only.
