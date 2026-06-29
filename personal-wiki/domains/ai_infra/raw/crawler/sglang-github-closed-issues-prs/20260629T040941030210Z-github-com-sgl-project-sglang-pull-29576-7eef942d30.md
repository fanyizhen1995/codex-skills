---
source_id: sglang-github-closed-issues-prs
title: Fix DSA indexer fusion bug causing excessive memory consumption.
canonical_url: https://github.com/sgl-project/sglang/pull/29576
captured_at: '2026-06-29T04:09:41.030210+00:00'
content_hash: 7eef942d30d66117e1559cecfbe5a54706affbb4604be02a23f5e1df6488f32b
---
# Fix DSA indexer fusion bug causing excessive memory consumption.

URL: https://github.com/sgl-project/sglang/pull/29576
State: closed
Labels: run-ci
Closed at: 2026-06-28T21:11:08Z
Merged at: 2026-06-28T21:11:08Z

https://github.com/sgl-project/sglang/pull/29564 found this bug. It's actually from the incorrect creation of rope buffer per layer x context length. Now, it will be 0.25 gb/GPU.

on TP 4 GLM-5.2:

Fusion before fix: 2,019,520 tok/pool
With disable: 2,398,784 tok/pool

After this PR: 2,394,496 tok/pool

Thanks! @mmangkad 











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28327159392](https://github.com/sgl-project/sglang/actions/runs/28327159392)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28327162406](https://github.com/sgl-project/sglang/actions/runs/28327162406)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
