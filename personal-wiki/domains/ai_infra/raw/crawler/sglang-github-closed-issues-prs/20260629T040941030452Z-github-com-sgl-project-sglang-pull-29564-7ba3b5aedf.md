---
source_id: sglang-github-closed-issues-prs
title: Disable DSA indexer fusion by default
canonical_url: https://github.com/sgl-project/sglang/pull/29564
captured_at: '2026-06-29T04:09:41.030452+00:00'
content_hash: 7ba3b5aedf5dc17b7bc167cc47415eb2c946a8d27e234c5f7af1e33d54d4270c
---
# Disable DSA indexer fusion by default

URL: https://github.com/sgl-project/sglang/pull/29564
State: closed
Labels: lora, deepseek
Closed at: 2026-06-28T20:40:19Z
Merged at: 

## Summary

I think we should consider making the DSA indexer fusion from #27705 opt-in for now. In the GLM-5.2 NVFP4 setup below, the memory/capacity cost looks large enough that I think it outweighs the perf benefit as the default tradeoff.

For TP4 with MTP enabled, the difference looks like this:

| Machine | Fusion | Target mem | KV capacity |
|---|---|---:|---:|
| B300 | off | ~108 GB weights / ~98 GB KV | ~1.90M tokens |
| B300 | on | ~127 GB weights / ~78 GB KV | ~1.52M tokens |
| GB300 | off | ~108 GB weights / ~105 GB KV | ~2.04M tokens |
| GB300 | on | ~127 GB weights / ~85 GB KV | ~1.66M tokens |

So this costs about `19.5 GB` of KV cache per rank, or roughly `380k` tokens of capacity, on this setup.

The TP2 case with MTP enabled is even more noticeable because the starting KV budget is much smaller. With `--mem-fraction-static 0.95` and `--max-running-requests 16`:

| Machine | Fusion | Target mem | KV capacity |
|---|---|---:|---:|
| B300 | off | ~211 GB weights / ~30 GB KV | ~582k tokens |
| B300 | on | ~231 GB weights / ~10 GB KV | ~199k tokens |
| GB300 | off | ~211 GB weights / ~38 GB KV | ~736k tokens |
| GB300 | on | ~231 GB weights / ~18 GB KV | ~353k tokens |

So in TP2, the same memory hit drops capacity by roughly `383k` tokens.

That feels large enough that I think the lower-memory path may be the better default tradeoff.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28322068551](https://github.com/sgl-project/sglang/actions/runs/28322068551)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28322068510](https://github.com/sgl-project/sglang/actions/runs/28322068510)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
