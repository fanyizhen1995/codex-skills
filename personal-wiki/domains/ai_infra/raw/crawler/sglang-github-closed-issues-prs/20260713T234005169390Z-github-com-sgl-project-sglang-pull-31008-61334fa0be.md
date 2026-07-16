---
source_id: sglang-github-closed-issues-prs
title: '[Spec] Deduplicate spec-v2 worker lifecycle boilerplate into BaseSpecWorker'
canonical_url: https://github.com/sgl-project/sglang/pull/31008
captured_at: '2026-07-13T23:40:05.169390+00:00'
content_hash: 61334fa0be997a33ddd18f2c49bf79a8bf4962414f9488f4287514b7ead8077d
---
# [Spec] Deduplicate spec-v2 worker lifecycle boilerplate into BaseSpecWorker

URL: https://github.com/sgl-project/sglang/pull/31008
State: closed
Labels: 
Closed at: 2026-07-13T18:48:40Z
Merged at: 2026-07-13T18:48:40Z

Move the copy-pasted `_get_plan_stream` (3 copies) to `spec_utils.get_plan_stream`, and lift the identical lifecycle delegation (`alloc_memory_pool` / `init_attention_backends` / `init_cuda_graphs` / `target_worker` / `draft_worker` / `clear_cache_pool`) from the eagle-family workers into `BaseSpecWorker` defaults. Pure move, no behavior change (-135/+54).



















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29236519437](https://github.com/sgl-project/sglang/actions/runs/29236519437)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29236519040](https://github.com/sgl-project/sglang/actions/runs/29236519040)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
