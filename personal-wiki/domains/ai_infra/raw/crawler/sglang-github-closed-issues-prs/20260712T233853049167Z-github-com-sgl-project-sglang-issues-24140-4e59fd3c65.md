---
source_id: sglang-github-closed-issues-prs
title: what's sglang metrics (num_running_reqs, num_queue_reqs) mean ?
canonical_url: https://github.com/sgl-project/sglang/issues/24140
captured_at: '2026-07-12T23:38:53.049167+00:00'
content_hash: 4e59fd3c651653cbe49d65e1f0fae560148e643f06b969a8cd7163695be04d87
---
# what's sglang metrics (num_running_reqs, num_queue_reqs) mean ?

URL: https://github.com/sgl-project/sglang/issues/24140
State: closed
Labels: inactive
Closed at: 2026-07-12T00:35:41Z
Merged at: 

The document said:
"num_running_reqs": The number of running requests
"num_queue_reqs": The number of requests in the waiting queue

But I found that sometimes num_running_reqs = 0, but num_queue_reqs is very high. According to your explanation, this is obviously unreasonable. If there are no requests being processed, why are there still so many in the queue?
