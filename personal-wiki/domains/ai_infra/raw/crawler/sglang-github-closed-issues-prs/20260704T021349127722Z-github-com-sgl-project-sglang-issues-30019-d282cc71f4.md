---
source_id: sglang-github-closed-issues-prs
title: MambaRadixCache shape mismatch in PD chunked prefill when caching unfinished
  req
canonical_url: https://github.com/sgl-project/sglang/issues/30019
captured_at: '2026-07-04T02:13:49.127722+00:00'
content_hash: d282cc71f4b2fdd1f981f19d382f34714e56b7f72a9afdd4bf9b31762a139375
---
# MambaRadixCache shape mismatch in PD chunked prefill when caching unfinished req

URL: https://github.com/sgl-project/sglang/issues/30019
State: closed
Labels: 
Closed at: 2026-07-03T07:43:18Z
Merged at: 

### Checklist

- [x] I have searched existing issues and did not find the same failure mode.
- [x] This is a correctness/stability bug, not a question.

### Environment

- SGLang version: `v0.5.12.post1`
- SGLang commit: `5a15cde858ea09b77116212a39356f2fc51b8584`
- Deployment mode: prefill/decode disaggregation
- Tensor parallel size per engine: `4`
- Workload: long-context rollout with chunked prefill enabled by the scheduler
- Model family: Qwen3.6 27B / hybrid attention with Mamba state cache

### What happened

A prefill scheduler process crashed while caching an unfinished chunked prefill request into `MambaRadixCache`.

The failing path is:

```text
scheduler.event_loop_normal_disagg_prefill()
  -> get_next_disagg_prefill_batch_to_run()
  -> process_prefill_chunk()
  -> maybe_cache_unfinished_req(self.chunked_req, self.tree_cache, chunked=True)
  -> tree_cache.cache_unfinished_req(req, **kwargs)
  -> mamba_radix_cache.py:659
       mamba_value_forked = self.req_to_token_pool.mamba_pool.fork_from(mamba_value)
  -> memory_pool.py:405 fork_from()
  -> memory_pool.py:393 copy_from()
       self.mamba_cache.conv[i][:, dst_index] = self.mamba_cache.conv[i][:, src_index]
```

The exception is:

```text
RuntimeError: shape mismatch: value tensor of shape [48, 1, 251, 1, 2560, 3]
cannot be broadcast to indexing result of shape [48, 1, 2560, 3]
```

This happened on all TP ranks of the same prefill engine. After that the prefill instance exited, and decode side requests cascaded into `KVTransferError`, `Connection refused`, and router `500 Internal Server Error` responses.

### Why this looks wrong

`MambaPool.fork_from()` allocates exactly one destination Mamba cache slot:

```python
dst_index = self.alloc(1)
self.copy_from(src_index, dst_index)
```

So the source index passed to `fork_from()` should identify one final Mamba state slot. In the failing chunked-prefill path, `mamba_value` appears to carry extra batch/chunk/time dimensions instead. PyTorch advanced indexing then expands the source tensor to:

```text
[48, 1, 251, 1, 2560, 3]
```

while the destination expects one cache slot:

```text
[48, 1, 2560, 3]
```

This suggests that `cache_unfinished_req(..., chunked=True)` can pass a non-scalar/non-single-slot Mamba value into the radix-cache fork path.

### Expected behavior

Caching unfinished chunked prefill requests should not crash the scheduler. For correctness, if the code cannot prove that the Mamba value is exactly one final state slot, it should not insert that Mamba state into radix cache. A cache miss/re-prefill is preferable to corrupting the radix cache or crashing the prefill instance.

### Minimal safe workaround / patch direction

A conservative mitigation is to guard just before `fork_from()` in `MambaRadixCache.cache_unfinished_req()`:

```python
if mamba_value is None or mamba_value.numel() != 1:
    logger.warning(
        "Skip Mamba radix cache for req=%s in cache_unfinished_req: "
        "expected one final Mamba state slot, got shape=%s, numel=%s",
        getattr(req, "rid", None),
        tuple(mamba_value.shape) if mamba_value is not None else None,
        mamba_value.numel() if mamba_value is not None else None,
    )
    return _skip_cache_unfinished_req(req)

mamba_value_forked = self.req_to_token_pool.mamba_pool.fork_from(mamba_value)
```

This keeps the normal single-slot path unchanged and only skips the problematic Mamba radix-cache insert. It turns the failure into a cache miss instead of a scheduler crash.

A more complete fix may need to identify why chunked prefill sometimes produces a multi-element `mamba_value` here, and either select the correct final state slot or avoid attempting Mamba radix insertion for that request.

### Related issues

- #24221 discusses Mamba radix cache correctness around chunked prefill / overlap scheduling and snapshot timing.
- #22326 tracks Mamba state checkpointing / state cache design work.
