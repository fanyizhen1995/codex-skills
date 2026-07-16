---
source_id: sglang-github-closed-issues-prs
title: 'amd/deepseek_v4: drop is_v4_compressed short-circuit so V4 uses SWAChunkCache'
canonical_url: https://github.com/sgl-project/sglang/pull/25398
captured_at: '2026-07-11T23:37:37.775627+00:00'
content_hash: 0b989ce0c89014b32751a226100e5871689c01c31b40d4f9c39a621140e4f49b
---
# amd/deepseek_v4: drop is_v4_compressed short-circuit so V4 uses SWAChunkCache

URL: https://github.com/sgl-project/sglang/pull/25398
State: closed
Labels: deepseek
Closed at: 2026-05-15T12:23:12Z
Merged at: 

## Summary

When sglang is launched with both `--disable-radix-cache` **and** `SGLANG_OPT_DPSK_V4_RADIX=1`, the scheduler crashes every TP rank on the first incoming request with:

```
AttributeError: 'ChunkCache' object has no attribute 'sliding_window_size'
  at schedule_policy.py:541 in _swa_budget_for_req
```

## Root cause

The bug requires two PRs to collide:

1. PR #23787 (`amd/deepseek_v4 integration 0426`) introduced an extra clause in `scheduler.py` that routes V4 compressed runs back to plain `ChunkCache` even when `is_hybrid_swa` is True:

   ```python
   is_v4_compressed = getattr(self.model_config, "is_swa_with_compressed_attention", False)
   if not self.is_hybrid_swa or is_v4_compressed:
       self.tree_cache = ChunkCache(params)
   else:
       self.tree_cache = SWAChunkCache(params)
   ```

   At the time this clause was added, no V4 model was ever marked `is_hybrid_swa=True`, so the `or is_v4_compressed` branch was dead code — its inclusion was a no-op.

2. PR #25164 (22/N) enabled `SGLANG_OPT_DPSK_V4_RADIX=1`, which marks V4 as a hybrid SWA model. With `is_hybrid_swa=True`, the `or is_v4_compressed` branch first becomes reachable, and it now redirects V4 compressed runs to plain `ChunkCache` — which does not carry a `sliding_window_size`, while the rest of the scheduler (`_swa_budget_for_req`, `maybe_evict_swa`, `_evict_swa`) continues to walk the SWA path and dereferences that attribute.

Upstream `main` does not have the `is_v4_compressed` clause; this PR aligns `amd/deepseek_v4` with the main-line behavior.

## Change

Remove the `is_v4_compressed` clause and the dead local:

```diff
 if effective_chunked_prefill_size is not None and self.disable_radix_cache:
-    is_v4_compressed = getattr(
-        self.model_config, "is_swa_with_compressed_attention", False
-    )
-    if not self.is_hybrid_swa or is_v4_compressed:
+    if not self.is_hybrid_swa:
         from sglang.srt.mem_cache.chunk_cache import ChunkCache
         self.tree_cache = ChunkCache(params)
     else:
         from sglang.srt.mem_cache.chunk_cache import SWAChunkCache
         self.tree_cache = SWAChunkCache(params)
```

After the change, V4 compressed runs with `--disable-radix-cache + SGLANG_OPT_DPSK_V4_RADIX=1` use `SWAChunkCache` like every other hybrid SWA model. `SWAChunkCache` is a subclass of `ChunkCache` that adds `sliding_window_size`; the V4 SWA budget / eviction paths are then reached with a tree_cache that already exposes the attribute, with no schedule_policy.py change needed.

## Behavior surface

The only config whose `tree_cache` selection changes is `is_hybrid_swa=True AND is_v4_compressed=True`. All other combinations are unaffected:

| `is_hybrid_swa` | `is_v4_compressed` | before | after |
|---|---|---|---|
| False | False | ChunkCache | ChunkCache |
| False | True | (unreachable today) | (unreachable today) |
| True | False | SWAChunkCache | SWAChunkCache |
| **True** | **True** | **ChunkCache (crashes)** | **SWAChunkCache (works)** |

A repo-wide grep finds zero `isinstance(..., ChunkCache)` checks that would be sensitive to the substitution.

## Reproduction

Branch `bug/dsv4-chunkcache-22n-radix1-0515` is a minimal repro:

* Code: 22/N (`de1aebe50`) + the flash_mla HIP guard (so ROCm boots).
* `repro/run_dsv4.sh` is the launch script with `SGLANG_OPT_DPSK_V4_RADIX=1 + --disable-radix-cache`.

Link: https://github.com/XinyuJiangCMU/sglang/tree/bug/dsv4-chunkcache-22n-radix1-0515

The `repro/run_dsv4.sh` commit message has step-by-step instructions; in short, after `bash repro/run_dsv4.sh` reaches `Application startup complete`, any `/v1/completions` request crashes every TP rank on `schedule_policy.py:541`.

## Validation (this PR's branch)

On 8x MI350X (ROCm 7.2, rocm/sgl-dev:rocm720-mi35x-721f045-20260513-DSv4):

* CUDA graph capture completes cleanly
* `Application startup complete` reached, server stable
* 25+ `/v1/completions` requests across single-stream, multi-round sequential, longer prompt (174 tokens), different sampling params, stop tokens, and streaming SSE — all returned correct output, zero `Scheduler hit / AttributeError / Traceback / Aborted` in the server log
* `sglang.bench_one_batch_server --batch-size 1 --input-len 128 --output-len 128` completes with TTFT 2.61s, decode 46.8 tok/s

## Test plan

- [x] Server reaches ready under the bug-triggering config (`SGLANG_OPT_DPSK_V4_RADIX=1` + `--disable-radix-cache`)
- [x] Sanity request succeeds against the same server (was the original crash signature)
- [x] Sequential 10-request and multi-round smoke pass with zero exceptions
- [x] Streaming SSE works
- [x] No `isinstance(..., ChunkCache)` regressions across the repo

Co-authored-by: Zhiyao Jiang <jessicajiang324@gmail.com>

<!-- pr-states:start -->
---
### CI States

Latest PR Test: <!-- slot:pr-test:start -->:x: **Missing `run-ci` label** — add it to run CI tests.<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: **Blocked** — `run-ci` is required first.<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
