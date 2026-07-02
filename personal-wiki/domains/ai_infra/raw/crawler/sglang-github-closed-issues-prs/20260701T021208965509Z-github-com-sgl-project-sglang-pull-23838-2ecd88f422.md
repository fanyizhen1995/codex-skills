---
source_id: sglang-github-closed-issues-prs
title: '[Speculative Decoding] Validate vocabulary compatibility in STANDALONE mode'
canonical_url: https://github.com/sgl-project/sglang/pull/23838
captured_at: '2026-07-01T02:12:08.965509+00:00'
content_hash: 2ecd88f4229cefcf4437dd173e6fc132ff80df5eb8c688618541e0aa9e50a454
---
# [Speculative Decoding] Validate vocabulary compatibility in STANDALONE mode

URL: https://github.com/sgl-project/sglang/pull/23838
State: closed
Labels: documentation, speculative-decoding, run-ci
Closed at: 2026-06-29T21:45:13Z
Merged at: 2026-06-29T21:45:13Z

## Motivation

`STANDALONE` speculative decoding requires the draft model to share the same vocabulary as the target model. If the vocabularies differ, draft token IDs map to different strings in the target vocabulary, making the speculative decoding lossy — the output distribution no longer matches what the target model would produce alone. Previously, SGLang silently accepted any draft model with no error or warning.

**Concrete example with real models** (`google/gemma-2-9b` as target, `bigcode/tiny_starcoder_py` as draft):

The STANDALONE token-ID data flow is: (1) draft forward pass → token IDs, (2) target verifies those IDs, (3) target decodes accepted IDs into the final string. If the two tokenizers map the same integer to different strings, every accepted draft token is silently wrong.

<details>
<summary><b>Without the fix (<code>main</code> branch)</b></summary>

```
$ python scripts/demo_vocab_mismatch_bug.py --mode buggy

======================================================================
Target : google/gemma-2-9b
Draft  : bigcode/tiny_starcoder_py  (WRONG — different tokenizer family)
======================================================================
  target vocab_size : 256,000
  draft  vocab_size : 49,152

Sample token IDs that decode to different strings in each vocabulary:
      ID           gemma-2-9b                tiny_starcoder_py
  ------  ----------------------------  ----------------------------
       4            '<mask>'                         ''
       5           '<2mass>'                         ''
       6           '[@BOS@]'                         ''
       7          '<unused0>'                        ''
       8          '<unused1>'                        ''
       9          '<unused2>'                        ''

======================================================================
Simulating the STANDALONE token-ID data flow
  step 1 — draft encodes prompt    (uses draft vocabulary)
  step 2 — target verifies IDs     (skipped in this simulation)
  step 3 — target decodes accepted IDs  (uses TARGET vocabulary)
======================================================================
  prompt         : 'def add(a, b): return a + b'
  draft IDs      : [589, 1015, 26, 83, 30, 323, 711, 442, 312, 474, 323]
  target decodes : ' = imp<unused19><unused76><unused23>jure…'  <<< SILENT CORRUPTION

  prompt         : 'The capital of France is'
  draft IDs      : [1318, 18926, 432, 45600, 438]
  target decodes : 'те वि… Pix…'  <<< SILENT CORRUPTION

  prompt         : 'import numpy as np'
  draft IDs      : [465, 6436, 619, 2065]
  target decodes : '…Showue Be'  <<< SILENT CORRUPTION

======================================================================
MODE: buggy  —  main branch, no vocab validation

  SGLang accepts the launch arguments without any error or warning.
  Inference runs; every accepted draft token is silently corrupted.

  The command that would silently succeed on main:

    python -m sglang.launch_server \
        --model-path google/gemma-2-9b \
        --speculative-algorithm STANDALONE \
        --speculative-draft-model-path bigcode/tiny_starcoder_py \
        --speculative-num-steps 5 \
        --speculative-eagle-topk 1 \
        --speculative-num-draft-tokens 5

  (no ValueError, no warning — server starts and corrupts silently)
```

</details>

<details>
<summary><b>With the fix (<code>standalone-vocab-check</code> branch)</b></summary>

```
$ python scripts/demo_vocab_mismatch_bug.py --mode fixed

  [... same corruption output as above ...]

======================================================================
MODE: fixed  —  standalone-vocab-check branch, validation active

  StandaloneWorker._validate_vocab_compatibility is called during
  __init__, after both models are loaded, before serving any request.

  ValueError raised at startup:

    STANDALONE speculative decoding requires the draft model to share the
    same vocabulary as the target model, but got target vocab_size=256000
    and draft vocab_size=49152. To use draft models with different
    vocabularies, use --speculative-algorithm TLI instead.

  Server exits immediately; no corrupted output is ever produced.
```

</details>

## Modifications

**`python/sglang/srt/speculative/standalone_worker.py`**

Adds `StandaloneWorker._validate_vocab_compatibility()`, a static method called at the end of `__init__` (after both models are loaded). It raises `ValueError` in two cases:

1. **`vocab_size` mismatch** — fast necessary check; catches obvious cross-family pairs (e.g. Llama 128k vs. Qwen 152k).
2. **`get_vocab()` dict mismatch** — catches the subtler case where both models have the same `vocab_size` but different token-to-ID mappings (e.g. different tokenizer families that happen to be the same size). Skipped when either tokenizer is `None` (`--skip-tokenizer-init`). This is the same approach used by HuggingFace Transformers ([PR #35029](https://github.com/huggingface/transformers/pull/35029)) to distinguish homogeneous from heterogeneous vocabulary pairs.

Both error messages point users to `--speculative-algorithm TLI` for cross-family pairs (see companion PR [#22883](https://github.com/sgl-project/sglang/pull/22883)).

**`test/registered/unit/spec/test_standalone_vocab_check.py`**

8 CPU-only unit tests (no server, no GPU) registered in `stage-a-test-cpu`:

| Test | What it checks |
|---|---|
| `test_identical_vocab_passes` | Same size + same mapping → no error |
| `test_mismatched_vocab_size_raises` | Different sizes → `ValueError` with sizes in message |
| `test_same_size_different_mapping_raises` | Same size, different token strings → `ValueError` |
| `test_none_target_tokenizer_skips_mapping_check` | `None` target tokenizer → only size checked |
| `test_none_draft_tokenizer_skips_mapping_check` | `None` draft tokenizer → only size checked |
| `test_both_tokenizers_none_skips_mapping_check` | Both `None` → only size checked |
| `test_error_message_contains_vocab_sizes` | Size-mismatch error includes both sizes |
| `test_error_message_suggests_tli_for_size_mismatch` | Both error types suggest `TLI` |

No behaviour change for existing valid STANDALONE configurations (same-family, same-vocab pairs).

## Accuracy Tests

N/A — this change only adds a startup validation; it does not modify any model forward pass or token selection logic.

## Speed Tests and Profiling

N/A — the validation runs once at server startup and has no impact on inference throughput.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).




















































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28356370156](https://github.com/sgl-project/sglang/actions/runs/28356370156)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28356369823](https://github.com/sgl-project/sglang/actions/runs/28356369823)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
