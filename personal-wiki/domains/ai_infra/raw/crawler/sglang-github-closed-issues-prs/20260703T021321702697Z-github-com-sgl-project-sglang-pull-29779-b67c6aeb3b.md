---
source_id: sglang-github-closed-issues-prs
title: Share one logits output buffer across prefill/decode/draft cuda-graph runners
canonical_url: https://github.com/sgl-project/sglang/pull/29779
captured_at: '2026-07-03T02:13:21.702697+00:00'
content_hash: b67c6aeb3bab56e33578cdf4f2a2bd5f59e8e86967ad5e69c6b51f8e21a806ff
---
# Share one logits output buffer across prefill/decode/draft cuda-graph runners

URL: https://github.com/sgl-project/sglang/pull/29779
State: closed
Labels: run-ci, run-ci-extra
Closed at: 2026-07-02T06:30:56Z
Merged at: 2026-07-02T06:30:56Z

Let each CUDA-graph runner (prefill / decode / draft) share one next-token logits output buffer `(bsz, vocab)`.

Size the shared buffer from the decode graph's needs (`max_decode_logits_rows`). Prefill computes logits eagerly (outside its graph), so it borrows the shared buffer when its rows fit and falls back to an eager allocation otherwise.































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28548387849](https://github.com/sgl-project/sglang/actions/runs/28548387849)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28548387805](https://github.com/sgl-project/sglang/actions/runs/28548387805)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
