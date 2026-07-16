---
source_id: sglang-github-closed-issues-prs
title: '[Spec] Key DP-attention graph admission on raw sync request counts'
canonical_url: https://github.com/sgl-project/sglang/pull/31245
captured_at: '2026-07-15T23:40:28.354212+00:00'
content_hash: b795db74d50dcdc91966f972cb54dd13a8c593d213db6fea8c5ef4e25f82a463
---
# [Spec] Key DP-attention graph admission on raw sync request counts

URL: https://github.com/sgl-project/sglang/pull/31245
State: closed
Labels: 
Closed at: 2026-07-15T20:03:41Z
Merged at: 2026-07-15T20:03:41Z

Stacks on #31244. Under DP attention, `can_run_graph` recovered the request count by dividing the spec-scaled `global_num_tokens_cpu` back by a per-runner width, guarded by a per-algorithm enumeration (`is_eagle() or is_standalone() or is_dflash_family()`) that silently breaks for new algorithms. The pre-scaling values already ride on `ForwardBatch.original_global_num_tokens_cpu` and are per-rank request counts on decode-family rounds (precedent: the multi-layer draft-extend runner already reads it), so the five sites now read them directly:

- `decode_cuda_graph_runner` / `eagle_draft` / `eagle_draft_extend` / `multi_layer_eagle_draft_extend`: `max(original_global_num_tokens_cpu)` — the multiply-then-divide round trip and the algorithm enumeration are gone.
- `frozen_kv_mtp`: keeps its own `// topk` (expanded-batch to graph-key mapping, mirroring its non-gather branch); only the unit-conversion half of the old `// topk * topk` divisor is removed.

Equivalent by construction wherever the old path was reachable: the scale factor applied at `ForwardBatch` build time equals the width the old code divided back out.























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29382374258](https://github.com/sgl-project/sglang/actions/runs/29382374258)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29382374157](https://github.com/sgl-project/sglang/actions/runs/29382374157)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
