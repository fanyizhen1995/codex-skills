---
source_id: sglang-github-closed-issues-prs
title: '[test] Set init-static attrs in mm_process_config mock fixtures'
canonical_url: https://github.com/sgl-project/sglang/pull/30766
captured_at: '2026-07-10T23:37:20.324904+00:00'
content_hash: 42a8a0ab3cac8d038998c6921fbd3e19fc10295afc17076153b1015f80284330
---
# [test] Set init-static attrs in mm_process_config mock fixtures

URL: https://github.com/sgl-project/sglang/pull/30766
State: closed
Labels: run-ci
Closed at: 2026-07-10T10:00:01Z
Merged at: 2026-07-10T10:00:01Z

## Problem

`test/registered/unit/managers/test_mm_process_config.py` fails on `main` after #30709 (`[style] Extract init-static values in tokenizer + multimodal path`):

```
ERROR: test_ernie45_vl_injects_images_kwargs (TestOverrideProcessorsConfigInjection)
  File ".../test_mm_process_config.py", line 245
    proc.process_mm_data("test", images=["img1"], videos=["vid1"])
  File ".../ernie45_vl.py", line 352, in process_mm_data
    if not self.keep_mm_feature_on_device:
AttributeError: 'Ernie4_5_VLImageProcessor' object has no attribute 'keep_mm_feature_on_device'
```

**Failing run** (head `873a9757e1`, before this fix): https://github.com/sgl-project/sglang/actions/runs/29073631869/job/86300524782 — `base-b-test-1-gpu-small (8)`, `test_mm_process_config.py::test_ernie45_vl_injects_images_kwargs`.

#30709 extracted `keep_mm_feature_on_device` / `disable_fast_image_processor` / `skip_tokenizer_init` from runtime `self.server_args.X` reads into `BaseMultimodalProcessor.__init__` instance attrs (`base_processor.py:191-193`), and switched `ernie45_vl.py` + `base_processor.py` reads to the instance attrs.

Two test helpers in `test_mm_process_config.py` (`_make_base_processor`, `_make_override_processor`) mock `__init__` to `lambda self: None` and only set `proc.server_args`, so the instance attrs are never assigned. Any `process_mm_data` call then hits `AttributeError` on `self.keep_mm_feature_on_device` / `self.disable_fast_image_processor` / `self.skip_tokenizer_init` (4 read sites in `base_processor.py`: lines 442, 476, 838, 1240).

This is deterministic on `main` itself (not env-dependent); `base-b-test-1-gpu-small` just hasn't run on `main` since #30709 merged (02:36Z), so CI hasn't surfaced it yet.

## Fix

Mirror the three init-static attrs from `server_args` in both mock-`__init__` helpers, matching the extraction #30709 added to the real `__init__`. Pure test-fixture adaptation — no production code changed.

`_make_processor` (uses the real `__init__`) is unaffected and left alone.

## Related

Same class of test-fixture gap as #30708's `HybridAttnBackend.__init__` extraction (mock `model_runner` missing `server_args`). CC @hnyls2002 (author of #30709).

## Checklist

- [x] Pure test fixture change, no behavior change
- [x] `pre-commit run` passes
- [x] `py_compile` passes
