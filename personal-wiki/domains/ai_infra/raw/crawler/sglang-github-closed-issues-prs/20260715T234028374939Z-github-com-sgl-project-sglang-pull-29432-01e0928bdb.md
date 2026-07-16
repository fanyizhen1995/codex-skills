---
source_id: sglang-github-closed-issues-prs
title: Fix bookkeeping fields not encapsulated with real allocations in normal alloc,
  PD pre-alloc, DFlash and EAGLE
canonical_url: https://github.com/sgl-project/sglang/pull/29432
captured_at: '2026-07-15T23:40:28.374939+00:00'
content_hash: 01e0928bdbc21e2e88a2b1cc50bca69468287413d469a549d4089841f6e884af
---
# Fix bookkeeping fields not encapsulated with real allocations in normal alloc, PD pre-alloc, DFlash and EAGLE

URL: https://github.com/sgl-project/sglang/pull/29432
State: closed
Labels: bypass-fastfail
Closed at: 2026-07-15T06:52:22Z
Merged at: 2026-07-15T06:52:22Z

Part of the `req_pool_idx` / cache / owned-KV decoupling — a stacked refactor chain.

Encapsulate the `req.kv.kv_allocated_len` bookkeeping with the real allocation in
every path (normal alloc, PD pre-alloc, DFlash, EAGLE): each physical alloc updates
its own bookkeeping inside one function instead of at a far-away glue site. Extracts
`alloc_for_decode_prealloc` / `alloc_for_decode_prealloc_hisparse` (kept in
`decode.py`) and the spec-decode alloc into `allocation.py`.

## Commits: rewrite + certified plain moves

Every pure relocation is a machine-checked extract/move; each semantic reshape is a
separate equivalence-reviewed commit. The spec-decode alloc is unified into one
`alloc_for_spec_decode` (no `dsv4_npu_aware` flag): DFlash routes through the same device
dispatch as EAGLE. That folds one small **deliberate** DFlash change into the final commit
— behavior-identical on CUDA and non-DSV4 NPU; on DSV4 + Ascend NPU DFlash now takes the
DSV4 reserve path like EAGLE (DFlash never shipped a real NPU path, so that corner was
dead). Everything else is behavior-equivalent to the reviewed / CI-tested op42 (the only
other deltas are the certified extractions' own code shape).

1. **Relocate `assign_req_to_token_pool` triton helpers** (`897ec989`) — pure relocation
   `speculative/triton_ops/cache_locs.py` -> `mem_cache/allocation.py` (certified).
2. **prepare: de-self the decode prealloc blocks** (`d137711a`) — in-place de-self +
   co-locate the `req.kv` bookkeeping; no relocation (equivalence-reviewed).
3. **extract `alloc_for_decode_prealloc[_hisparse]`** (`9a38be94`) — certified extract-function.
4. **prepare: rewrite the EAGLE alloc block to a canonical de-batched form** (`b186c2f4`) —
   de-batch, `num_needed_tokens > 0` guard, explicit dispatch, tail bookkeeping (equivalence-reviewed).
5. **extract `alloc_for_spec_decode`** (`052364c0`) — certified extract-function.
6. **encapsulate remaining bookkeeping + unify the spec-decode dispatch** (`748f0b69`) —
   DFlash rewire, the `alloc_for_extend` / `alloc_for_decode` `req.kv.kv_allocated_len`
   updates, and routing DFlash through the shared `alloc_for_spec_decode` device dispatch.

### Verify the certified moves

All four certified relocations in this stack (op40's extract + op42's three) reproduce
byte-for-byte from their base via faithful relocation primitives:

```bash
gh gist clone ec486009606de4216efe8359131da16c /tmp/ch31-proofs
cd <sglang-repo-root>
bash /tmp/ch31-proofs/verify_all.sh     # PASS x4
```

---
Stacked on: `op40`. Aggregated CI sandbox: #28636.

































































































































































































































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29395463209](https://github.com/sgl-project/sglang/actions/runs/29395463209)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29395463145](https://github.com/sgl-project/sglang/actions/runs/29395463145)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
