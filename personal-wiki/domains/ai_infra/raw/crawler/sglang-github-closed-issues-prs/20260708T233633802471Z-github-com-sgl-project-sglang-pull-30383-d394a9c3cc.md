---
source_id: sglang-github-closed-issues-prs
title: '[CI] Fix DSA top-k v2 test metadata'
canonical_url: https://github.com/sgl-project/sglang/pull/30383
captured_at: '2026-07-08T23:36:33.802471+00:00'
content_hash: d394a9c3cced4a5d8ed0d38ea90c50dbafb36a208249486b2feafdc1926c4153
---
# [CI] Fix DSA top-k v2 test metadata

URL: https://github.com/sgl-project/sglang/pull/30383
State: closed
Labels: run-ci
Closed at: 2026-07-08T02:04:09Z
Merged at: 

## Summary

Fix `test_dsa_indexer.py` by populating `DSAMetadata.topk_v2_plan` for the top-k v2 path broken by #30274

### Before

```bash
python test/registered/kernels/test_dsa_indexer.py

.........FFF.
======================================================================
FAIL: test_topk_fused_backends_equivalence (__main__.TestDSAIndexer.test_topk_fused_backends_equivalence) (tie_break=None, topk_transform_method='PAGED', with_row_starts=False)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/sgl-workspace/test/registered/kernels/test_dsa_indexer.py", line 968, in test_topk_fused_backends_equivalence
    self._run_fused_topk_backend_equivalence_test(
  File "/sgl-workspace/test/registered/kernels/test_dsa_indexer.py", line 676, in _run_fused_topk_backend_equivalence_test
    out_sgl = metadata_sgl.topk_transform(
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/python/sglang/srt/layers/attention/dsa_backend.py", line 318, in topk_transform
    return self.topk_backend.topk_transform(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/python/sglang/srt/layers/attention/dsa/dsa_topk_backend.py", line 111, in topk_transform
    return _topk_transform_v2_paged(logits, lengths, topk, attn_metadata)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/python/sglang/srt/layers/attention/dsa/dsa_topk_backend.py", line 291, in _topk_transform_v2_paged
    plan is not None and plan.shape[0] == num_rows + 1
AssertionError: topk_v2_plan must be preprocessed per forward (see DSAMetadata.topk_v2_plan)

======================================================================
FAIL: test_topk_fused_backends_equivalence (__main__.TestDSAIndexer.test_topk_fused_backends_equivalence) (tie_break='small', topk_transform_method='PAGED', with_row_starts=False)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/sgl-workspace/test/registered/kernels/test_dsa_indexer.py", line 968, in test_topk_fused_backends_equivalence
    self._run_fused_topk_backend_equivalence_test(
  File "/sgl-workspace/test/registered/kernels/test_dsa_indexer.py", line 676, in _run_fused_topk_backend_equivalence_test
    out_sgl = metadata_sgl.topk_transform(
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/python/sglang/srt/layers/attention/dsa_backend.py", line 318, in topk_transform
    return self.topk_backend.topk_transform(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/python/sglang/srt/layers/attention/dsa/dsa_topk_backend.py", line 111, in topk_transform
    return _topk_transform_v2_paged(logits, lengths, topk, attn_metadata)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/python/sglang/srt/layers/attention/dsa/dsa_topk_backend.py", line 291, in _topk_transform_v2_paged
    plan is not None and plan.shape[0] == num_rows + 1
AssertionError: topk_v2_plan must be preprocessed per forward (see DSAMetadata.topk_v2_plan)

======================================================================
FAIL: test_topk_fused_backends_equivalence (__main__.TestDSAIndexer.test_topk_fused_backends_equivalence) (tie_break='large', topk_transform_method='PAGED', with_row_starts=False)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/sgl-workspace/test/registered/kernels/test_dsa_indexer.py", line 968, in test_topk_fused_backends_equivalence
    self._run_fused_topk_backend_equivalence_test(
  File "/sgl-workspace/test/registered/kernels/test_dsa_indexer.py", line 676, in _run_fused_topk_backend_equivalence_test
    out_sgl = metadata_sgl.topk_transform(
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/python/sglang/srt/layers/attention/dsa_backend.py", line 318, in topk_transform
    return self.topk_backend.topk_transform(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/python/sglang/srt/layers/attention/dsa/dsa_topk_backend.py", line 111, in topk_transform
    return _topk_transform_v2_paged(logits, lengths, topk, attn_metadata)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/python/sglang/srt/layers/attention/dsa/dsa_topk_backend.py", line 291, in _topk_transform_v2_paged
    plan is not None and plan.shape[0] == num_rows + 1
AssertionError: topk_v2_plan must be preprocessed per forward (see DSAMetadata.topk_v2_plan)

----------------------------------------------------------------------
Ran 11 tests in 9.341s

FAILED (failures=3)
sys:1: DeprecationWarning: builtin type swigvarlink has no __module__ attribute
```

### After

```bash
python test/registered/kernels/test_dsa_indexer.py

...........
----------------------------------------------------------------------
Ran 11 tests in 9.310s

OK
sys:1: DeprecationWarning: builtin type swigvarlink has no __module__ attribute
```





































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28860200606](https://github.com/sgl-project/sglang/actions/runs/28860200606)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28860200460](https://github.com/sgl-project/sglang/actions/runs/28860200460)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
