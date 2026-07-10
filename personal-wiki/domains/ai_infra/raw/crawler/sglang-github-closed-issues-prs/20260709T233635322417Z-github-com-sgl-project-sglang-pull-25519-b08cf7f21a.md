---
source_id: sglang-github-closed-issues-prs
title: '[Quantization][bugfix] Correct E8M0 NaN-sentinel detection in e8m0_to_f32'
canonical_url: https://github.com/sgl-project/sglang/pull/25519
captured_at: '2026-07-09T23:36:35.322417+00:00'
content_hash: b08cf7f21aeaaa349b9da0a333c35340426ef8b1f1ae30ef4ac36f01f923f988
---
# [Quantization][bugfix] Correct E8M0 NaN-sentinel detection in e8m0_to_f32

URL: https://github.com/sgl-project/sglang/pull/25519
State: closed
Labels: amd
Closed at: 2026-07-09T22:02:54Z
Merged at: 2026-07-09T22:02:54Z

## Motivation

`e8m0_to_f32` in `python/sglang/srt/layers/quantization/quark/utils.py` decodes
OCP MX-format v1.0 e8m0 (uint8 unsigned exponent, no mantissa) into float32
scales. Per spec, encoded `0..254` represents `2^(x − 127)` and encoded `255`
is reserved to represent **NaN**.

The existing predicate compared on the post-conversion float (`x_f32 == 128`)
instead of the integer encoding (`x == 255`), producing **two coupled errors**
on a single line:

| Encoded `x`              | `x_f32 = 2^(x − 127)` (float32)         | `x_f32 == 128`? | Code did                  | Spec       |
|--------------------------|------------------------------------------|-----------------|---------------------------|------------|
| `134` (legit scale 128.0)| `2^7 = 128.0`                            | **True**        | replaced with **NaN**     | keep `128.0` |
| `255` (NaN sentinel)     | `2^128` → **`+inf`** (fp32 overflow)     | False           | left as `+inf`            | **NaN**    |

So legitimate scales of exactly `128.0` were poisoned to NaN, and the actual
NaN sentinel passed through as `+inf`.

**Blast radius** — a single in-tree caller: `quark_post_load_weights` in the
same file (`quark/utils.py:202`), used on the MXFP4 path for
`kv_b_proj.weight_scale` of DeepSeek-style MLA models
(`amd/DeepSeek-R1-0528-MXFP4`, `amd/Kimi-K2.5-MXFP4`, `amd/GLM-5-MXFP4`, etc.).

The bug has been latent because (a) per-block scales of exactly `128.0` are
rare in typical pretrained weights, and (b) Quark only emits the NaN sentinel
for all-zero / unrepresentable blocks, which is uncommon for MLA
`kv_b_proj`. When either fires, downstream `w * w_scales` saturates to `inf` /
`NaN` — usually loud rather than silently wrong.

## Modifications

### `python/sglang/srt/layers/quantization/quark/utils.py`

One functional-line change in `e8m0_to_f32`; comment block rewritten to
document the OCP semantics and prevent reintroducing the same bug:

```diff
 def e8m0_to_f32(x):
-    # Convert the input tensor `x` (assumed to be in e8m0 format) to float32.
-    # e8m0 is a custom 8-bit floating point format with 8 bits for exponent, 0 for mantissa.
-    # This means the value is essentially 2^(exponent - 127), similar to how IEEE-754 stores floats.
-    # Convert x to float32 for computation, and compute the power of 2 by subtracting the bias (127).
+    # Per OCP MX-format v1.0: encoded 0..254 -> 2^(x-127); encoded 255 -> NaN.
+    # Detect the sentinel on the raw integer encoding, not on the float result
+    # (in float32, 2^128 overflows to +inf, so the old `x_f32 == 128` predicate
+    # both missed x=255 and wrongly NaN'd legitimate scale 128.0 at x=134).
     x_f32 = 2 ** ((x.to(torch.float32)) - 127)
-    # If the exponent value was 255 (i.e., 2^(128)), this is a special case usually used to represent NaN or Inf.
-    # Since this custom format has no mantissa, treat 2^128 as NaN.
-    x_f32[x_f32 == 128] = float("nan")
+    x_f32[x == 255] = float("nan")
     return x_f32
```

### `test/registered/unit/layers/quantization/test_quark_utils.py` (new)

New unit-test file using `CustomTestCase`, registered with
`register_cpu_ci(est_time=5, suite="base-a-test-cpu")`. Covers both bug facets
plus guardrails:

| Test | Purpose |
|---|---|
| `test_scale_128_is_not_nan` | `x = 134` must decode to `128.0`, not NaN |
| `test_nan_sentinel` | `x = 255` must decode to NaN |
| `test_only_255_is_nan` | across `0..255`, **exactly** index `255` is NaN |
| `test_known_powers_of_two` | spot-checks `2^-127, 0.25, 0.5, 1.0, 2.0, 4.0, 128.0, 2^127` |
| `test_zero_exponent_is_one` | guardrail (passes on both buggy and fixed code) |
| `test_shape_preserved` | guardrail |
| `test_cuda_parity` | GPU-only spot check, skipped on CPU-only hosts |

> **Note** — incidental formatter change. `ruff format` (project-mandated lint
> step) merged two adjacent string literals in an unrelated
> `raise_aiter_import_error` message in the same file
> (`"Failed to import aiter. " "Make sure ..."` → single string). This is a
> one-line stylistic auto-fix from the formatter, not a deliberate refactor.

## Accuracy Tests

### Unit-level

Against the unfixed `main`, the 4 bug-catching tests fail and the 2 guardrails
pass; after the fix, all 7 pass (or 6 + 1 skipped on a CPU-only host).

**Pre-fix:**

```console
$ pytest test/registered/unit/layers/quantization/test_quark_utils.py -v
... 5 failed, 2 passed ...     # 4 bug-catchers + CUDA-parity fail
```

**Post-fix:**

```console
$ pytest test/registered/unit/layers/quantization/test_quark_utils.py -v
... 7 passed ...
```

**Sanity smoke** on `[0, 127, 134, 254, 255]`:

| Encoded | Before fix | After fix |
|---|---|---|
| `0`   | `5.88e-39` | `5.88e-39` |
| `127` | `1.0`      | `1.0`      |
| `134` | **`nan`** ❌ | `128.0` ✓ |
| `254` | `1.70e38`  | `1.70e38`  |
| `255` | **`inf`** ❌ | `nan` ✓   |

### End-to-end (recommended before merge — TODO)

Greedy-decode parity (deterministic) on `amd/DeepSeek-R1-0528-MXFP4` TP=8:

```bash
python -m sglang.bench_one_batch \
  --model amd/DeepSeek-R1-0528-MXFP4 \
  --batch-size 1 --input-len 256 --output-len 64 --tp 8 \
  --disable-radix-cache --random-seed 0
```

Compare token IDs before/after. Two acceptable outcomes:

- **Identical** → buggy predicate didn't fire on this checkpoint's actual
  scales; fix prevents future regression.
- **Differ** → bug *was* firing in real weights; outputs should be sensible
  (gsm8k 5-shot neutral or higher).

## Speed Tests and Profiling

Not applicable. `e8m0_to_f32` runs once per `weight_scale` tensor at
model-load time (inside `quark_post_load_weights`), not in the inference hot
path. The change is one predicate; no kernel or hot-path impact is expected.
No benchmarking required.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit). Full `pre-commit run` on changed files passes: `black`, `isort`, `codespell`, `ruff`, `check-registered-tests`.
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests). New `test_quark_utils.py` under `test/registered/unit/layers/quantization/`, suite `base-a-test-cpu`.
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations). *Not applicable — internal helper, no public docs reference it.*
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed). *Unit-level above; e2e greedy-decode parity on `amd/DeepSeek-R1-0528-MXFP4` recommended pre-merge — TODO.*
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers — tag AMD/Quark reviewers (use `git blame` on `quark/utils.py`).
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests).
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.

















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28313701584](https://github.com/sgl-project/sglang/actions/runs/28313701584)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28313701543](https://github.com/sgl-project/sglang/actions/runs/28313701543)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
