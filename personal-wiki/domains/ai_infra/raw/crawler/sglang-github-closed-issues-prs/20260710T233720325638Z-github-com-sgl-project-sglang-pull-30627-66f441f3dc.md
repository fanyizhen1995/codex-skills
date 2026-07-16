---
source_id: sglang-github-closed-issues-prs
title: Fix CuTe DSL DSA paged MQA export
canonical_url: https://github.com/sgl-project/sglang/pull/30627
captured_at: '2026-07-10T23:37:20.325638+00:00'
content_hash: 66f441f3dc8d9f4159deb9be3225469f81e038a8b51af332c49f31ba3221693b
---
# Fix CuTe DSL DSA paged MQA export

URL: https://github.com/sgl-project/sglang/pull/30627
State: closed
Labels: run-ci, jit-kernel
Closed at: 2026-07-10T08:32:59Z
Merged at: 2026-07-10T08:32:59Z

## Summary

Fix the CuTe DSL paged MQA export that got broken by the import reordering in #30374. Before this change, the export pointed at the module instead of the function. This puts the order back so callers get the function again.

I also made the CuTe DSL helper import CUDA-only. For NPU, ROCm, and other backends, we leave a `None` placeholder instead of trying to load CUDA-only code.













































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29079820810](https://github.com/sgl-project/sglang/actions/runs/29079820810)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29079820631](https://github.com/sgl-project/sglang/actions/runs/29079820631)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
