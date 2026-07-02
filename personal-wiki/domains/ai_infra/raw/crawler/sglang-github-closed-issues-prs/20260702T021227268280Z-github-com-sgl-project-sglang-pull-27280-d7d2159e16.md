---
source_id: sglang-github-closed-issues-prs
title: ' [Test] Add GQA correctness tests for context_attention_fwd'
canonical_url: https://github.com/sgl-project/sglang/pull/27280
captured_at: '2026-07-02T02:12:27.268280+00:00'
content_hash: d7d2159e16c698942ee429306ccefc05e9cb7f6437ee4a5d01f3a9e507054561
---
#  [Test] Add GQA correctness tests for context_attention_fwd

URL: https://github.com/sgl-project/sglang/pull/27280
State: closed
Labels: jit-kernel
Closed at: 2026-07-01T05:09:15Z
Merged at: 

  ## Motivation

  The existing tests for `context_attention_fwd` only cover MHA cases where `num_heads == num_kv_heads`. GQA
  (Grouped Query Attention) is not covered. This leaves a correctness gap for the prefill attention path.

  ## Modifications

  - Add GQA test cases to `context_attention_fwd` correctness tests (`num_kv_heads < num_heads`)
  - Fix `max_input_len` handling for `seq_len=128` config

  ## Accuracy Tests

  All 72/72 tests pass on A10G:
  - MHA configs (existing): pass
  - GQA configs (new): num_kv_heads ∈ {2, 4, 8} with num_heads=32, pass
  - Reference: PyTorch SDPA, max diff < 1e-2
...
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads1-128-seq_config0] PASSED [ 76%]
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads1-128-seq_config1] PASSED [ 77%]
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads1-128-seq_config2] PASSED [ 79%]
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads1-128-seq_config3] PASSED [ 80%]
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads1-128-seq_config4] PASSED [ 81%]
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads1-128-seq_config5] PASSED [ 83%]
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads2-64-seq_config0] PASSED [ 84%]
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads2-64-seq_config1] PASSED [ 86%]
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads2-64-seq_config2] PASSED [ 87%]
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads2-64-seq_config3] PASSED [ 88%]
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads2-64-seq_config4] PASSED [ 90%]
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads2-64-seq_config5] PASSED [ 91%]
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads2-128-seq_config0] PASSED [ 93%]
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads2-128-seq_config1] PASSED [ 94%]
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads2-128-seq_config2] PASSED [ 95%]
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads2-128-seq_config3] PASSED [ 97%]
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads2-128-seq_config4] PASSED [ 98%]
../test_context_attention.py::test_context_attention_fwd[dtype0-False-num_heads2-128-seq_config5] PASSED [100%]
 ============================== 72 passed, 5 warnings in 21.81s ==============================

  ## Speed Tests and Profiling

  N/A — this PR adds tests only, no kernel changes.

  ## Checklist

  - [x] Format your code according to pre-commit
  - [x] Add unit tests
  - [ ] Update documentation — N/A
  - [x] Provide accuracy benchmark
  - [x] Follow SGLang code style







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #26961401186](https://github.com/sgl-project/sglang/actions/runs/26961401186)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #26961401674](https://github.com/sgl-project/sglang/actions/runs/26961401674)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
