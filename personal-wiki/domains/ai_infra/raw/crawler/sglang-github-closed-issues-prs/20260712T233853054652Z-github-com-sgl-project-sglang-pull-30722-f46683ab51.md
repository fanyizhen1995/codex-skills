---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Cherry-pick AMD fixes into release/v0.5.15'
canonical_url: https://github.com/sgl-project/sglang/pull/30722
captured_at: '2026-07-12T23:38:53.054652+00:00'
content_hash: f46683ab513701059cfe5707d6d4a22001eee51c2afa894e4cb052cf1ea0a759
---
# [AMD] Cherry-pick AMD fixes into release/v0.5.15

URL: https://github.com/sgl-project/sglang/pull/30722
State: closed
Labels: amd, deepseek, hicache, sgl-kernel, jit-kernel
Closed at: 2026-07-12T19:25:51Z
Merged at: 

## Summary

Cherry-picks the finalized AMD-related PR list from `main` into `release/v0.5.15`. **9 PRs included.** Applied in chronological (landing) order, each with `-x` provenance. `#30237` and `#30333` were verified already present in `release/v0.5.15`.

| PR | Title | Source commit (on `main`) | Apply |
|----|-------|---------------------------|-------|
| #30313 | [AMD] Cap DSV4 Flash max_total_num_tokens | `dabd4cfcfd349eb8c3c3a15210fd74978335a812` | clean |
| #30302 | [AMD][MORI-EP] Skip LocalExpertCount kernel in decode graph when not recording | `9ddea8d9efb3c16bfa35df07681de5c05e5eb041` | clean |
| #30374 | [AMD] Fix DeepSeekV4 server cutlass error | `40a68521c9c325cf2757c05e7a476ad4e54f8038` | clean |
| #29275 | Fix gfx95 bpreshuffle FP8 activation scale layout | `8d2b66fd9071f29434f5f0a149be1f6829907c2f` | clean |
| #30265 | [AMD] Fix GLM-5.2 MTP Quark excludes | `07ef650ef7b066f8bab81d531acb1edc8231902d` | conflict resolved |
| #30557 | [AMD] Fix AITER custom all-gather CUDA-graph capture crash under torch_memory_saver | `bd7e54d7379e437cf5f027382d6ca214e046626b` | clean |
| #29479 | [AMD] fix dsv4 indexer dtype dispatch on gfx950 | `336b64ecce300a3cefc615d84b6780e22f83a89c` | clean |
| #30339 | [AMD] Fix stale SWA ring buffer on radix prefix reuse for DeepSeek-V4 (unified_kv) | `462b6171bd80902f68a0056c41bf95e0cec91400` | clean |
| #29417 | [AMD] Enable unified-KV HiCache on DeepSeek-V4 | `8d0fd341507710d628bf3e05d88ae87253970b78` | clean |

## Conflict resolutions (please review)

- **#30265**: kept release's `get_flags` import, added `WeightsMapper` (verified present in release `models/utils.py`), and added only `GlmMoeDsaForCausalLMNextN` to the arch lists (the upstream Longcat entries were pre-existing context on `main`, absent in release, so not introduced).

## Not included

- **#28534** ([AMD] Enable JIT staged HiCache write-back and fix CPU-index crash): **dropped.** It was authored on top of **#30249** ("[mem_cache][6/N] move MHA host-pool into pool_host/mha.py", not in release), so its diff and its added test reference the post-move path `mem_cache/pool_host/mha.py`, which doesn't exist in `release/v0.5.15`. Rather than carry it without #30249, it is deferred; can be revisited together with #30249.
- **#30415** (Enable RDNA3/4 gfx1100/gfx1201): dropped from the finalized list.
- **#27436** ([diffusion] breakable CUDA graph for DiTs, `33c3dfd7`): deferred — depends on **#29742** ("fix z-Image accuracy", not in release); release's `patchify_and_embed()` returns a 5-tuple while #27436 expects the 7->8-tuple form, so it can't be cherry-picked cleanly on its own.

## Test plan

- [ ] AMD CI on `release/v0.5.15` (pr-test-amd) green
- [ ] Sanity-check #30265 on ROCm hardware
- [ ] Follow-ups: #28534 (with #30249), and #27436 (with #29742)

_Note: blocked/pending #24651 per the release coordination thread._







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29067430598](https://github.com/sgl-project/sglang/actions/runs/29067430598)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29067430426](https://github.com/sgl-project/sglang/actions/runs/29067430426)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
