---
source_id: sglang-github-closed-issues-prs
title: Only log DCP status when DCP is enabled
canonical_url: https://github.com/sgl-project/sglang/pull/30184
captured_at: '2026-07-06T02:14:53.059790+00:00'
content_hash: 93c771ea97489ca049cf91471dd70324ec3b0c73b3f092908bee4f0ae27c5ae2
---
# Only log DCP status when DCP is enabled

URL: https://github.com/sgl-project/sglang/pull/30184
State: closed
Labels: 
Closed at: 2026-07-05T23:00:41Z
Merged at: 

## Motivation

The line

```
[2026-07-05 12:47:29] DCP disabled, dcp_size=1, tp_size=1
```

was logged on every startup that runs **without** decode context parallelism — i.e. the common case (`dcp_size=1`). It is pure noise for the vast majority of runs.

## Change

Drop the `else` branch that logs the disabled state in `initialize_model_parallel` (`python/sglang/srt/distributed/parallel_state.py`). The `DCP enabled, dcp_size=..., tp_size=...` log is kept, so we still get a one-line confirmation exactly when decode context parallelism is actually active (`decode_context_parallel_size > 1`).

No behavior change beyond logging.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28757849322](https://github.com/sgl-project/sglang/actions/runs/28757849322)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28757849277](https://github.com/sgl-project/sglang/actions/runs/28757849277)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
