---
source_id: sglang-github-closed-issues-prs
title: Speculative decoding support on XPU
canonical_url: https://github.com/sgl-project/sglang/pull/23180
captured_at: '2026-07-03T02:13:21.703671+00:00'
content_hash: e9471cec91853d5ced79f9325ba11ab73432d65379ef1ede615c31cd7f8f863c
---
# Speculative decoding support on XPU

URL: https://github.com/sgl-project/sglang/pull/23180
State: closed
Labels: intel, xpu, run-ci, run-ci-extra
Closed at: 2026-07-02T05:23:24Z
Merged at: 2026-07-02T05:23:24Z

This PR add support of speculative decoding feature for XPU utilizing explicit triton path.

It also adds build and verify tree kernels in triton.

Currently it supports below algorithms with greedy flow:

- [x] Standalone algorithm
- [x] Eagle algorithm
- [x] Eagle3 algorithm


Future works:
1. Adding support for NGRAM
2. Adding support for intel_xpu attention backend
3. DFLASH decoding

JH...!

























































































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28498338912](https://github.com/sgl-project/sglang/actions/runs/28498338912)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28498338770](https://github.com/sgl-project/sglang/actions/runs/28498338770)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
