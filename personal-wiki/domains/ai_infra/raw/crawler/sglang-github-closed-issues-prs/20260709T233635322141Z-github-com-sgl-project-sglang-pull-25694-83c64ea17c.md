---
source_id: sglang-github-closed-issues-prs
title: '[Quantization][Bugfix]: Join multi-arg RuntimeError in Quark _check_scheme_supported'
canonical_url: https://github.com/sgl-project/sglang/pull/25694
captured_at: '2026-07-09T23:36:35.322141+00:00'
content_hash: 83c64ea17c0a8f05d084718b27e45fb3bed6b6f5c57e3c5ee30919e8bfee1ef0
---
# [Quantization][Bugfix]: Join multi-arg RuntimeError in Quark _check_scheme_supported

URL: https://github.com/sgl-project/sglang/pull/25694
State: closed
Labels: 
Closed at: 2026-07-09T22:07:15Z
Merged at: 2026-07-09T22:07:15Z

## Motivation

`QuarkConfig._check_scheme_supported` raises a capability-mismatch error like this:

```python
raise RuntimeError(
    "Quantization scheme is not supported for ",
    f"the current GPU. Min capability: {min_capability}. ",
    f"Current capability: {capability}.",
)
```

That passes **three positional arguments** to `RuntimeError`. `Exception.__str__` formats `self.args` as a tuple repr when `len(args) != 1`, so the message the user actually sees today is the tuple-stringified mess on the left, not the intended sentence on the right:

| Today (buggy) | After this PR |
|---|---|
| `('Quantization scheme is not supported for ', 'the current GPU. Min capability: 200. ', 'Current capability: 70.')` | `Quantization scheme is not supported for the current GPU. Min capability: 200. Current capability: 70.` |

Parens, quoted fragments, and quote-comma joins all leak through — what looked like three message fragments meant to be concatenated were instead stored as three separate `args` entries.

## Modifications

**`python/sglang/srt/layers/quantization/quark/quark.py:187-192`** — replace the three-argument call with a single message built via adjacent string-literal concatenation. The diff is a two-character semantic change (drop two commas) plus a short clarifying comment:

```python
raise RuntimeError(
    "Quantization scheme is not supported for "
    f"the current GPU. Min capability: {min_capability}. "
    f"Current capability: {capability}."
)
```

No other code paths in the function change.

**`test/registered/unit/layers/quantization/test_quark_config.py`** (new) — CPU-only regression test registered to `base-a-test-cpu` (`est_time=5`). Six cases:

| Test | Purpose | On unfixed code |
|---|---|---|
| `test_error_is_single_argument` | structural — asserts `len(err.args) == 1` | **fails** (gets 3 args) |
| `test_error_message_renders_as_sentence` | rejects leading `(` and quote-comma fragment joins | **fails** |
| `test_error_message_content` | substring sanity check on the rendered message | passes either way |
| `test_unsupported_returns_false_when_error_disabled` | guardrail for `error=False` branch | passes |
| `test_supported_returns_true` | guardrail for the `supported` path | passes |
| `test_no_device_returns_false` | guardrail for `get_device_capability() is None` | passes |

The test mocks `sglang.srt.layers.quantization.quark.quark.get_device_capability` and uses `QuarkConfig.__new__(QuarkConfig)` to skip `__init__` (the method under test reads no instance attributes).

## Accuracy Tests

N/A — this is an error-formatting fix. It does not touch quantization math, kernel selection, or any model-output code path. The exception is raised only on the unsupported-capability branch; values returned by `_check_scheme_supported` (`True` / `False`) are unchanged.

## Speed Tests and Profiling

N/A — no kernel changes, no hot-path modifications. The change is to an exception-construction expression that only fires on a fatal-startup error.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations) — N/A; bug fix, no API/behavior change.
- [x] Provide accuracy and speed benchmark results — see above; not applicable.
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).













<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28313702146](https://github.com/sgl-project/sglang/actions/runs/28313702146)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28313702094](https://github.com/sgl-project/sglang/actions/runs/28313702094)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
