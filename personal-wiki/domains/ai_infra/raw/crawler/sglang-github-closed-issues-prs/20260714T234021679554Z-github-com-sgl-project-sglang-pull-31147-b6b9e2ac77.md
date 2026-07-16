---
source_id: sglang-github-closed-issues-prs
title: Extract kv cache dtype configuration into mem_cache
canonical_url: https://github.com/sgl-project/sglang/pull/31147
captured_at: '2026-07-14T23:40:21.679554+00:00'
content_hash: b6b9e2ac77d79a71414993e2d8d89de918a953e56bd438a4d89cd7d52889509c
---
# Extract kv cache dtype configuration into mem_cache

URL: https://github.com/sgl-project/sglang/pull/31147
State: closed
Labels: 
Closed at: 2026-07-14T07:52:40Z
Merged at: 2026-07-14T07:52:40Z

### mrc-kv-cache-dtype(extract-kv-cache-dtype-prep,non_mechanical_provable): Prep configure_kv_cache_dtype for extraction: @staticmethod + kwargs + 2-tuple return

De-self in place: the method becomes a kwargs @staticmethod returning the
(resolved_kv_cache_dtype, kv_cache_dtype) 2-tuple; the call site unpacks the
tuple, records the resolved string, and keeps the DFLASH fa4 draft override
inline. The body stays at its original position in the class. Stage the
destination module header (imports + logger + _is_hip) so the move lands in
an existing module.

### mrc-kv-cache-dtype(extract-kv-cache-dtype-move,mechanical_provable): Move configure_kv_cache_dtype + TORCH_DTYPE_TO_KV_CACHE_STR to mem_cache.kv_cache_dtype (cut+paste)

### mrc-kv-cache-dtype(kv-cache-dtype-wrapper-postpare,non_mechanical_provable): Reintroduce the configure_kv_cache_dtype orchestration wrapper and requalify through the kv_cache_dtype module import

Wrap the moved function back into the configure_kv_cache_dtype method
(tuple unpack + resolved-dtype recording + the DFLASH fa4 draft override)
and route the call through the kv_cache_dtype module import instead of the
bare function import.

### mrc-kv-cache-dtype(pass-kv-cache-dtype-string,non_mechanical_provable): Pass kv_cache_dtype string into configure_kv_cache_dtype and fold the DFLASH fa4 draft override into it

configure_kv_cache_dtype only ever read server_args.kv_cache_dtype, so take
that field directly and drop the ServerArgs dependency.

Forward-port adaptation for latest upstream/main: the fa4 draft KV-cache dtype
override now flows through the extracted configure_kv_cache_dtype free function.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29316032024](https://github.com/sgl-project/sglang/actions/runs/29316032024)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29316031818](https://github.com/sgl-project/sglang/actions/runs/29316031818)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
