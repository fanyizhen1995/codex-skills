---
source_id: sglang-github-closed-issues-prs
title: Fix CuTe DSL DSA paged MQA export
canonical_url: https://github.com/sgl-project/sglang/pull/30627
captured_at: '2026-07-11T23:37:37.770233+00:00'
content_hash: 1d5f807a755cdcd69226328b291bab3eb7bcfc7e46271ef7eface313b6437559
---
# Fix CuTe DSL DSA paged MQA export

URL: https://github.com/sgl-project/sglang/pull/30627
State: closed
Labels: run-ci, jit-kernel, post version patch
Closed at: 2026-07-10T08:32:59Z
Merged at: 2026-07-10T08:32:59Z

## Summary

Fix the CuTe DSL paged MQA export that got broken by the import reordering in #30374. Before this change, the export pointed at the module instead of the function. This puts the order back so callers get the function again.

I also made the CuTe DSL helper import CUDA-only. For NPU, ROCm, and other backends, we leave a `None` placeholder instead of trying to load CUDA-only code.

















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29079820810](https://github.com/sgl-project/sglang/actions/runs/29079820810)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #29147456875](https://github.com/sgl-project/sglang/actions/runs/29147456875)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
