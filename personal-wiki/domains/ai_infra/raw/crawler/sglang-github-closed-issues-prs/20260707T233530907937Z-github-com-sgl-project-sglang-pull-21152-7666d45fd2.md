---
source_id: sglang-github-closed-issues-prs
title: '[CI] Reduce NVFP4 CI running time'
canonical_url: https://github.com/sgl-project/sglang/pull/21152
captured_at: '2026-07-07T23:35:30.907937+00:00'
content_hash: 7666d45fd27ebedff663232a4c77c14510d2a62345c115981376e1dfbe294d28
---
# [CI] Reduce NVFP4 CI running time

URL: https://github.com/sgl-project/sglang/pull/21152
State: closed
Labels: blackwell
Closed at: 2026-07-07T17:44:20Z
Merged at: 

NVFP4 seems relatively well covered already. Also, the quantization preparation is not complicated, so it's OK to not have E2E for every backend.

<img width="608" height="427" alt="Screenshot 2026-03-22 at 4 48 57 PM" src="https://github.com/user-attachments/assets/b583498d-2da9-45cd-b0c8-a77093f6c24e" />

```
CUDA_VISIBLE_DEVICES=7 pytest /sgl-workspace/sglang/test/registered/quant/test_nvfp4_gemm.py
========================================================================================= test session starts =========================================================================================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0
rootdir: /sgl-workspace/sglang/test
configfile: pytest.ini
plugins: anyio-4.12.1, typeguard-4.5.1
collected 5 items                                                                                                                                                                                     

test/registered/quant/test_nvfp4_gemm.py ....s                                                                                                                                                  [100%]

========================================================================================== warnings summary ===========================================================================================
../../usr/local/lib/python3.12/dist-packages/_pytest/config/__init__.py:1428
  /usr/local/lib/python3.12/dist-packages/_pytest/config/__init__.py:1428: PytestConfigWarning: Unknown config option: asyncio_mode
  
    self._warn_or_fail_if_strict(f"Unknown config option: {key}\n")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=============================================================================== 4 passed, 1 skipped, 1 warning in 5.28s ===============================================================================
```
