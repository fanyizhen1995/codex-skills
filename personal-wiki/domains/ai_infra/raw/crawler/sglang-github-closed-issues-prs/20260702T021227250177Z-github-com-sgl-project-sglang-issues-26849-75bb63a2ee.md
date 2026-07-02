---
source_id: sglang-github-closed-issues-prs
title: '[Feature] HiSparse support status for DeepSeek-V4-Pro'
canonical_url: https://github.com/sgl-project/sglang/issues/26849
captured_at: '2026-07-02T02:12:27.250177+00:00'
content_hash: 75bb63a2ee4203344384d3e437f1176b24166f41c2170bd885ccf6dbb88eed31
---
# [Feature] HiSparse support status for DeepSeek-V4-Pro

URL: https://github.com/sgl-project/sglang/issues/26849
State: closed
Labels: 
Closed at: 2026-07-01T06:02:15Z
Merged at: 

### Checklist

- [x] If this is not a feature request but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Motivation

## HiSparse performance on DeepSeek-V4-Pro: lower throughput observed on current main branch

Hi SGLang team,

HiSparse is a very exciting feature, especially given the results reported in the LMSYS [DeepSeek-V4 on Day 0 blog](https://www.lmsys.org/blog/2026-04-25-deepseek-v4/), which mention up to a **3× improvement in overall token capacity and throughput for long-context serving**.

I was therefore eager to try it in my own deployment and attempted to reproduce the reported results on DeepSeek-V4-Pro using the current `main` branch at commit 38f32c38abd41a296bd21186b5d8c5e6af1f8997.

However, for the 100K-input / 40K-output workload, I observed that enabling HiSparse actually reduced peak output token throughput compared to the baseline. I also evaluated several other context-length and observed a similar trend.

Server logs indicate that after enabling HiSparse, the effective concurrency decreases. At the same time, I observed that the C4 pool becomes smaller.

Looking through the code, I found that:

- Enabling HiSparse reduces the C4 pool by the `host_to_device_ratio` factor. https://github.com/sgl-project/sglang/blob/38f32c38abd41a296bd21186b5d8c5e6af1f8997/python/sglang/srt/model_executor/pool_configurator.py#L418
- The direct-to-host path does not appear to have been implemented yet. https://github.com/sgl-project/sglang/blob/38f32c38abd41a296bd21186b5d8c5e6af1f8997/python/sglang/srt/managers/hisparse_coordinator.py#L252

It's entirely possible that I am missing some configuration details or that the blog results were obtained using a different branch, so I wanted to ask:

### Questions

1. Would it be possible to share the branch, benchmark scripts, and configuration used to produce the results reported in the blog post?
2. Is there an estimated timeline for when full HiSparse support for DeepSeek-V4-Pro will be available in the release branch?

Thank you for your work on this feature. Any clarification would be greatly appreciated.

### Related resources

_No response_
