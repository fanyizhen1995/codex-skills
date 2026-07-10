---
source_id: sglang-github-closed-issues-prs
title: Disable multi-threaded load by default when prefetch is on
canonical_url: https://github.com/sgl-project/sglang/pull/30146
captured_at: '2026-07-09T23:36:35.337853+00:00'
content_hash: 851901e7ef24e95f40b3e50b19a76ccfe18af955357586b7454a4380f9a36f13
---
# Disable multi-threaded load by default when prefetch is on

URL: https://github.com/sgl-project/sglang/pull/30146
State: closed
Labels: documentation, run-ci
Closed at: 2026-07-09T07:28:54Z
Merged at: 2026-07-09T07:28:54Z

## Summary

#20289 turned `enable_multithread_load` on by default. So when you also enable `--weight-loader-prefetch-checkpoints`, you get two things reading the same shards at the same time, the prefetch threads warming the page cache and the multi-threaded loader pulling the same files. On NFS/Lustre that's just I/O oversubscription and it tends to slow things down.

If prefetch is on (safetensors + mmap, not `FASTSAFETENSORS`), we now drop to single-threaded loading and let prefetch do its thing. If you actually want both, say on local NVMe where prefetch is basically a no-op and multi-threading still helps, set `enable_multithread_load` (or just `num_threads`) in `--model-loader-extra-config` to opt back in.

























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28731060421](https://github.com/sgl-project/sglang/actions/runs/28731060421)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28731060327](https://github.com/sgl-project/sglang/actions/runs/28731060327)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
