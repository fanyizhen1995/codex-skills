---
source_id: sglang-github-closed-issues-prs
title: Fix LTX2 RoPE JIT kernel CI
canonical_url: https://github.com/sgl-project/sglang/pull/30278
captured_at: '2026-07-07T23:35:30.921199+00:00'
content_hash: 7ecbd914a25190f22ee9f10f6a06de5e40e24638fa4b8d604d860e5cc556c05a
---
# Fix LTX2 RoPE JIT kernel CI

URL: https://github.com/sgl-project/sglang/pull/30278
State: closed
Labels: jit-kernel
Closed at: 2026-07-07T02:15:21Z
Merged at: 2026-07-07T02:15:21Z

```
python test/registered/jit/diffusion/test_ltx2_qknorm_split_rope.py
============================================================================================== test session starts ==============================================================================================
platform linux -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0 -- /usr/bin/python
cachedir: .pytest_cache
rootdir: /sgl-workspace/sglang/test
configfile: pytest.ini
plugins: anyio-4.14.1, typeguard-4.5.2
collected 5 items                                                                                                                                                                                               

test/registered/jit/diffusion/test_ltx2_qknorm_split_rope.py::test_ltx2_qknorm_split_rope_matches_torch_exactly[1-3-3-32-128] PASSED
test/registered/jit/diffusion/test_ltx2_qknorm_split_rope.py::test_ltx2_qknorm_split_rope_matches_torch_exactly[1-5-2-32-64] PASSED
test/registered/jit/diffusion/test_ltx2_qknorm_split_rope.py::test_ltx2_qknorm_split_rope_matches_torch_exactly[2-4-3-32-64] PASSED
test/registered/jit/diffusion/test_ltx2_qknorm_split_rope.py::test_ltx2_qknorm_split_rope_rejects_unsupported_inputs PASSED
test/registered/jit/diffusion/test_ltx2_qknorm_split_rope.py::test_ltx2_qknorm_split_rope_custom_op_torch_compile_fullgraph PASSED

=============================================================================================== warnings summary ================================================================================================
../../usr/local/lib/python3.12/dist-packages/_pytest/config/__init__.py:1309
../../usr/local/lib/python3.12/dist-packages/_pytest/config/__init__.py:1309
  /usr/local/lib/python3.12/dist-packages/_pytest/config/__init__.py:1309: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; anyio
    self._mark_plugins_for_rewrite(hook, disable_autoload)

../../usr/local/lib/python3.12/dist-packages/_pytest/config/__init__.py:1434
  /usr/local/lib/python3.12/dist-packages/_pytest/config/__init__.py:1434: PytestConfigWarning: Unknown config option: asyncio_mode
  
    self._warn_or_fail_if_strict(f"Unknown config option: {key}\n")

registered/jit/diffusion/test_ltx2_qknorm_split_rope.py: 14 warnings
  /usr/local/lib/python3.12/dist-packages/torch/jit/_script.py:365: DeprecationWarning: `torch.jit.script_method` is deprecated. Please switch to `torch.compile` or `torch.export`.
    warnings.warn(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================================================================================== 5 passed, 17 warnings in 1.40s =========================================================================================
```


Observed in https://github.com/sgl-project/sglang/actions/runs/28798849023/job/85396541208?pr=29690, https://github.com/sgl-project/sglang/actions/runs/28768180627/job/85296541953?pr=30117











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28806860654](https://github.com/sgl-project/sglang/actions/runs/28806860654)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28806860424](https://github.com/sgl-project/sglang/actions/runs/28806860424)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
